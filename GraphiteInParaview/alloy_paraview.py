import paraview.simple
import gompy.types.OGF as OGF
import numpy as np
import vtk
from vtk.util import numpy_support
import random

# TODO:
#  - general polygonal surfaces
#  - lines
#  - check when we can use deep=False
#  - maybe a mechanism to update vtk objects and keep them in sync
#    with geogram using SceneGraph's signals

def mesh_attributes_to_vtk(M: OGF.MeshGrob, loc: str, V: vtk.vtkDataSet):
    """
       @brief Copies geogram attributes to a vtk object
       @param[in] M a MeshGrob
       @param[in] loc one of 'vertices','edges','facets','cells'
       @param[in] V the target vtkDataSet, typically obtained through
                  getPointData() or getCellData()
                  from a vtkPolyData or vtkUnstructuredGrid
    """
    attrs = M.list_attributes(localisations=loc).split(';')
    for attr_name in attrs:
        if attr_name != '':
            np_attr = np.asarray(M.I.Editor.find_attribute(attr_name))
            vtk_attr = numpy_support.numpy_to_vtk(np_attr,deep=True)
            vtk_attr.SetName(attr_name.removeprefix(loc + '.'))
            V.AddArray(vtk_attr)

def mesh_to_vtk_points(M: OGF.MeshGrob):
    """
        @brief Converts a MeshGrob into a vtkPoints
        @param[in] M a MeshGrob
        @return a vtkPoints object, with the same geometry and attributes as M
    """
    np_points = np.asarray(M.I.Editor.get_points()).astype(np.float32)
    points = vtk.vtkPoints()
    points.SetData(numpy_support.numpy_to_vtk(np_points,deep=True))
    return points

def mesh_to_vtk_poly_data(M: OGF.MeshGrob):
    """
        @brief Converts a MeshGrob into a vtkPolyData (polygonal surface)
        @param[in] M a MeshGrob
        @return a vtkPolyData object, with the same geometry and attributes as M
    """
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
    mesh_attributes_to_vtk(M, 'vertices', vpd.GetPointData())
    mesh_attributes_to_vtk(M, 'facets', vpd.GetCellData())
    return vpd

def mesh_to_vtk_unstructured_grid(M: OGF.MeshGrob):
    """
        @brief Converts a MeshGrob into a vtkUnstructuredGrid
        @param[in] M a MeshGrob
        @return a vtkUnstructuredGrid, with the same geometry and attributes as M
    """
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
            # hex numbering differs in geogram and paraview
            swap_hex = np.asarray([0,1,3,2,4,5,7,6])
            # maps number of vertices to vtk primitive
            nbv_to_vtk = [ 0, 0, 0, 0,
                 vtk.VTK_TETRA,vtk.VTK_PYRAMID,vtk.VTK_WEDGE,0,vtk.VTK_HEXAHEDRON
            ]
            np_cell_vertices = np.asarray(M.I.Editor.get_cell_vertices())
            np_cell_ptrs = np.asarray(M.I.Editor.get_cell_pointers())
            for c in range(M.I.Editor.nb_cells): # argh! a Python loop (slooow)!
                c_begin = np_cell_ptrs[c]
                c_end = np_cell_ptrs[c+1]
                c_nv = c_end - c_begin
                np_c_vertices = np_cell_vertices[c_begin:c_end]
                vtk_c_vertices = vtk.vtkIdList()
                vtk_c_vertices.Allocate(c_nv)
                if c_nv == 8: # vertices numbering different for hex
                    np_c_vertices = np_c_vertices[swap_hex]
                for v in np_c_vertices: # aaarrrrgh ! two nested Python loops !!
                    vtk_c_vertices.InsertNextId(v)
                vug.InsertNextCell(nbv_to_vtk[c_nv], vtk_c_vertices)
    mesh_attributes_to_vtk(M, 'vertices', vug.GetPointData())
    mesh_attributes_to_vtk(M, 'cells', vug.GetCellData())
    return vug

def mesh_to_vtk(M: OGF.MeshGrob):
    """
       @brief Converts a MeshGrob into a vtk object
       @param[in] M the MeshGrob to be converted
       @return a vtkPoints, vtkPolyData or vtkUnstructuredGrid depending on
         the information present in M. Attributes are also copied.
    """
    if M.I.Editor.nb_cells != 0:
        return mesh_to_vtk_unstructured_grid(M)
    else:
        return mesh_to_vtk_poly_data(M)

def show_mesh(M: OGF.MeshGrob, name: str, color: list = [0.7, 0.7, 0.7]):
    """
       @brief Displays a Graphite MeshGrob in Paraview as a vtkPolyData
       @details If an object of the same name is already present in Paraview,
         it will be overwritten
       @param[in] M the MeshGrob to be displayed
       @param[in] name the name that will be associated with M in Paraview
       @param[in] color a list with the r,g,b component of the color
    """
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

def show_meshes(scene_graph: OGF.SceneGraph, prefix: str = ''):
    """
       @brief Displays all objects with a name that starts with a given prefix
       @param[in] scene_graph the scene_graph that contains the meshes to
                  be displayed
       @param[in] prefix if specified, display only the objects which name start
                  with prefix
    """
    for obj in scene_graph.objects:
        if obj.name.startswith(prefix):
            color = [ random.uniform(0,1),
                      random.uniform(0,1),
                      random.uniform(0,1) ]
            show_mesh(obj, obj.name, color)
