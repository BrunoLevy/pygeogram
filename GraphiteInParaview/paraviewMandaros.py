from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData

import paraview.simple
import gompy.types.OGF as OGF
import numpy as np
import vtk
from vtk.util import numpy_support
import random

def show_Alloy_mesh(M,name,color):
    """Displays a Graphite MeshGrob in Paraview as a vtkPolyData"""
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

sg = OGF.SceneGraph()
UVW = sg.load_object('mandaros_UVW.geogram')
dir(UVW.I)
UVW.I.Geomodel.build_structural_model_from_tet_mesh()

for obj in sg.objects:
    if obj.name.startswith('region_'):
      color = [ random.uniform(0,1), random.uniform(0,1), random.uniform(0,1)]
      show_Alloy_mesh(obj, obj.name, color)
