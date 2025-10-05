import paraview.simple
import gompy.types.OGF as OGF
import numpy as np
import vtk
from vtk.util import numpy_support
import random

def mesh_to_vtk_points(M):
    np_points = np.asarray(M.I.Editor.get_points()).astype(np.float32)
    points = vtk.vtkPoints()
    points.SetData(numpy_support.numpy_to_vtk(np_points,deep=True))
    return points

def mesh_to_vtk_poly_data(M):
    vpd = vtk.vtkPolyData()
    vpd.SetPoints(mesh_to_vtk_points(M))
    if M.I.Editor.nb_facets != 0:
        np_triangles = np.asarray(M.I.Editor.get_triangles())
        # vtk cell data needs number of vertices in each cell,
        # so we need to prepend a column of 3's
        np_triangles = np.c_[
            np.full(np_triangles.shape[0], 3, dtype=np.uint32), np_triangles
        ]
        np_triangles = np_triangles.astype(np.int64)
        triangles = vtk.vtkCellArray()
        triangles.SetCells(
           np_triangles.shape[0],
           numpy_support.numpy_to_vtkIdTypeArray(np_triangles, deep=True)
        )
        vpd.SetPolys(triangles)
    return vpd

def mesh_to_vtk_unstructured_grid(M):
    vug = vtk.vtkUnstructuredGrid()
    vug.SetPoints(mesh_to_vtk_points(M))
    if M.I.Editor.nb_cells != 0:
        if M.I.Editor.cells_are_simplices:
            np_tets = np.asarray(M.I.Editor.get_tetrahedra())
            # vtk cell data needs number of vertices in each cell,
            # so we need to prepend a column of 4's
            np_tets = np.c_[
                np.full(np_tets.shape[0], 4, dtype=np.uint32), np_tets
            ]
            np_tets = np_tets.astype(np.int64)
            tets = vtk.vtkCellArray()
            tets.SetCells(
                np_tets.shape[0],
                numpy_support.numpy_to_vtkIdTypeArray(np_tets, deep=True)
            )
            vug.SetCells(vtk.VTK_TETRA,tets)
        else:
            geogram_celltype2vtk = [
                vtk.VTK_TETRA, vtk.VTK_HEXAHEDRON, vtk.VTK_WEDGE,
                vtk.VTK_PYRAMID, vtk.VTK_TETRA
            ]
            geogram_celltype2nb = [ 4, 8, 6, 5, 4 ]
            # hex numbering differs in geogram and paraview
            swap_hex = np.asarray([0,1,3,2,4,5,7,6])
            np_cell_types = np.asarray(M.I.Editor.get_cell_types())
            np_cell_vertices = np.asarray(M.I.Editor.get_cell_vertices())
            np_cell_ptrs = np.asarray(M.I.Editor.get_cell_pointers())
            np_cell_sizes = np_cell_ptrs[1:] - np_cell_ptrs[0:-1]
            for c in range(M.I.Editor.nb_cells):
                c_begin = np_cell_ptrs[c]
                c_type = np_cell_types[c]
                c_nv = geogram_celltype2nb[c_type]
                np_c_vertices = np_cell_vertices[c_begin:c_begin+c_nv]
                vtk_c_vertices = vtk.vtkIdList()
                vtk_c_vertices.Allocate(c_nv)
                if c_type == 1:
                    np_c_vertices = np_c_vertices[swap_hex]
                for v in np_c_vertices:
                    vtk_c_vertices.InsertNextId(v)
                vug.InsertNextCell(
                    geogram_celltype2vtk[c_type], vtk_c_vertices
                )
    return vug

def mesh_to_vtk(M):
    if M.I.Editor.nb_cells != 0:
        return mesh_to_vtk_unstructured_grid(M)
    else:
        return mesh_to_vtk_poly_data(M)

def show_mesh(M,name,color):
    """Displays a Graphite MeshGrob in Paraview as a vtkPolyData"""
    old = paraview.simple.FindSource(name)
    if old != None:
        paraview.simple.Delete(old)
    vtkobject = mesh_to_vtk(M)
    tp = paraview.simple.TrivialProducer(guiName=name)
    tp.GetClientSideObject().SetOutput(vtkobject)
    display = paraview.simple.Show(tp)
    if M.I.Editor.nb_cells != 0:
        display.Representation = 'Surface With Edges'
    elif M.I.Editor.nb_facets != 0:
        display.Representation = 'Surface With Edges'
    else:
        display.Representation = 'Point Gaussian'
    display.DiffuseColor = color

def show_meshes(scene_graph, prefix=''):
    """Displays all objects with a name that starts with a given prefix"""
    for obj in scene_graph.objects:
        if obj.name.startswith(prefix):
            color = [ random.uniform(0,1),
                      random.uniform(0,1),
                      random.uniform(0,1) ]
            show_mesh(obj, obj.name, color)
