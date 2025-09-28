from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData

import paraview.simple
import gompy.types.OGF as OGF
import numpy as np
import vtk
from vtk.util import numpy_support

def show_Alloy_mesh(M):
    vpd = vtkPolyData()
    points_array = np.asarray(M.I.Editor.get_points()).astype(np.float32)
    points = vtkPoints()
    points.SetData(numpy_support.numpy_to_vtk(points_array,deep=True))
    vpd.SetPoints(points)
    triangles = np.asarray(M.I.Editor.get_triangles())
    triangles = np.c_[np.full(triangles.shape[0], 3, dtype=np.uint32), triangles]
    triangles = triangles.astype(np.int64)
    polys = vtkCellArray()
    polys.SetCells(
        triangles.shape[0],
        numpy_support.numpy_to_vtkIdTypeArray(triangles, deep=True)
    )
    vpd.SetPolys(polys)
    tp = paraview.simple.TrivialProducer()
    tp.GetClientSideObject().SetOutput(vpd)
    display = paraview.simple.Show(tp)
    display.Representation = 'Surface'
    display.DiffuseColor = [0.7, 0.7, 1.0]

S = OGF.MeshGrob()
S.I.Shapes.create_sphere()
show_Alloy_mesh(S)
