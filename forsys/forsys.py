from dataclasses import dataclass, field
import pandas as pd
import forsys.time_series as ts
import forsys.fmatrix as fmatrix
import forsys.pmatrix as pmatrix
import forsys.frames as fsframes
@dataclass
class ForSys():
    frames: dict

    cm: bool=True
    initial_guess: list = field(default_factory=list)

    def __post_init__(self):
        # if there is more than 1 time, generate time series
        if len(self.frames) > 1:
            self.mesh = ts.TimeSeries(self.frames, cm=self.cm, 
                                        initial_guess=self.initial_guess)
            
            self.times_to_use = self.mesh.times_to_use()
        else:
            self.mesh = {}
        
        self.force_matrices = {}
        self.pressure_matrices = {}
        self.forces = {k: None for k in range(len(self.frames))}
        self.pressures = {k: None for k in range(len(self.frames))}

    
    def build_force_matrix(self, when: int = 0, term: str = "none", metadata:dict = {}):
        # TODO: add matrix caching
        self.force_matrices[when] = fmatrix.ForceMatrix(self.frames[when],
                                # externals_to_use = self.frames[when].border_vertices,
                                externals_to_use = 'none',
                                term=term,
                                metadata=metadata,
                                timeseries=self.mesh)

    def build_pressure_matrix(self, when: int = 0):
        # TODO: add matrix caching
        self.pressure_matrices[when] = pmatrix.PressureMatrix(self.frames[when],
                                                              timeseries=self.mesh)
        

    def solve_stress(self, when: int = 0, **kwargs) -> None:
        self.forces[when] = self.force_matrices[when].solve(self.mesh, **kwargs)
        self.frames[when].forces = self.forces[when]
        self.frames[when].assign_tensions_to_big_edges()
        
    def solve_pressure(self, when: int=0, **kwargs):
        assert type(self.forces[when]) is not None, "Forces must be calculated first"
        self.pressures = self.pressure_matrices[when].solve_system(**kwargs)
        self.frames[when].assign_pressures(self.pressures, self.pressure_matrices[when].mapping_order)
        
    def get_accelerations():
        raise(NotImplementedError)
    
    def get_velocities():
        raise(NotImplementedError)

    def log_force(self, when: int):
        df = pd.DataFrame.from_dict(self.frames[when].forces, orient='index')
        df['is_border'] = [False if isinstance(x, int) else True for x in df.index]
        return df

    def get_edge_force(self, v0, v1, t0=-1, tmax=-1):
        """
        get lambda value for the edge given two vertices of the edge
        """
        edge_force = []
        if tmax == -1 or t0 == -1:
            range_values = self.mesh.mapping.keys()
        else:
            range_values = range(t0, tmax)

        for t in range_values:
            current_v0 = self.mesh.get_point_id_by_map(v0, t0, t)
            current_v1 = self.mesh.get_point_id_by_map(v1, t0, t)
            for e in self.frames[t].earr:
                if current_v0 in e and current_v1 in e:
                    edge_id = self.frames[t].earr.index(e)
            edge_force.append(self.frames[t].forces[edge_id])

        return edge_force          
            
            
    def remove_outermost_edges(self, frame_number: int, layers: int = 1) -> tuple:
        if layers == 0:
            return True
        elif layers > 1:
            raise(NotImplementedError)
        else:
            # vertex_to_delete = []
            border_cells_ids = [cell.id for cell in self.frames[0].cells.values() if cell.is_border]
            for cell_id in border_cells_ids:
                ### hardcoded remove after!
                if (self.frames[frame_number].time == 3 and cell_id == 43) \
                or (self.frames[frame_number].time == 17 and cell_id == 50) \
                or (self.frames[frame_number].time == 24 and cell_id == 9) \
                or (self.frames[frame_number].time == 28 and cell_id == 35) \
                or (self.frames[frame_number].time == 11 and cell_id == 39):
                    pass
                else:
                    self.remove_cell(frame_number, cell_id)            
                ###
                # self.remove_cell(frame_number, cell_id)            
            return self.frames[frame_number].vertices, self.frames[frame_number].edges, self.frames[frame_number].cells


    def remove_cell(self, frame_number: int, cell_id: int):
        vertex_to_delete = []
        for vertex in self.frames[frame_number].cells[cell_id].vertices:
            # if all(cid in border_cells_ids for cid in vertex.ownCells):
            if len(vertex.ownCells) < 2:
                assert vertex.ownCells[0] == self.frames[frame_number].cells[cell_id].id, "Vertex incorrectly placed in cell"
                for ii in vertex.ownEdges.copy():
                    del self.frames[frame_number].edges[ii]

                vertex_to_delete.append(vertex.id)
                # vertex.ownCells.remove(self.frames[frame_number].cells[cell_id].id)
                # vertex.remove_cell(cell_id)
        
        for vertex_id in list(set(vertex_to_delete)):
            del self.frames[frame_number].vertices[vertex_id]

        del self.frames[0].cells[cell_id]

        self.frames[frame_number] = fsframes.Frame(frame_number, 
                                                   self.frames[frame_number].vertices, 
                                                   self.frames[frame_number].edges, 
                                                   self.frames[frame_number].cells, 
                                                   time=self.frames[frame_number].time,
                                                   gt=self.frames[frame_number].gt,
                                                   surface_evolver=self.frames[frame_number].surface_evolver)
        return self.frames[frame_number]
