from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData

import paraview.simple
import gompy.types.OGF as OGF
import numpy as np
import vtk
from vtk.util import numpy_support
import random

def show_mesh(M,name,color):
    """Displays a Graphite MeshGrob in Paraview as a vtkPolyData"""
    old = paraview.simple.FindSource(name)
    if old != None:
        paraview.simple.Delete(old)
    vpd = vtkPolyData()
    points_array = np.asarray(M.I.Editor.get_points()).astype(np.float32)
    points = vtkPoints()
    points.SetData(numpy_support.numpy_to_vtk(points_array,deep=True))
    vpd.SetPoints(points)
    triangles = np.asarray(M.I.Editor.get_triangles())
    # vtk cell data needs number of vertices in each cell, so we need to prepend
    # a column of 3's
    triangles = np.c_[np.full(triangles.shape[0], 3, dtype=np.uint32), triangles]
    triangles = triangles.astype(np.int64)
    polys = vtkCellArray()
    polys.SetCells(
        triangles.shape[0],
        numpy_support.numpy_to_vtkIdTypeArray(triangles, deep=True)
    )
    vpd.SetPolys(polys)
    tp = paraview.simple.TrivialProducer(guiName=name)
    tp.GetClientSideObject().SetOutput(vpd)
    display = paraview.simple.Show(tp)
    display.Representation = 'Surface'
    display.DiffuseColor = color

def show_meshes(scene_graph, prefix=''):
    """Displays all objects with a name that starts with a given prefix"""
    for obj in scene_graph.objects:
        if obj.name.startswith(prefix):
            color = [ random.uniform(0,1),
                      random.uniform(0,1),
                      random.uniform(0,1) ]
            show_mesh(obj, obj.name, color)
