from vtkmodules.vtkCommonCore import (
    vtkFloatArray,
    vtkIdList,
    vtkPoints
)
from vtkmodules.vtkCommonDataModel import (
    vtkCellArray,
    vtkPolyData
)

import paraview.simple
import gompy.types.OGF as OGF
import numpy as np

def mkVtkIdList(it):
    vil = vtkIdList()
    for i in it:
        vil.InsertNextId(int(i))
    return vil

def show_Alloy_mesh(M):
    vpd = vtkPolyData()
    points = vtkPoints()
    polys = vtkCellArray()
    for i, xi in enumerate(np.asarray(M.I.Editor.get_points())):
        points.InsertPoint(i, xi)
    vpd.SetPoints(points)
    for pt in np.asarray(M.I.Editor.get_triangles()):
        polys.InsertNextCell(mkVtkIdList(pt))
    vpd.SetPolys(polys)
    tp = paraview.simple.TrivialProducer()
    tp.GetClientSideObject().SetOutput(vpd)
    display = paraview.simple.Show(tp)
    display.Representation = 'Surface'
    display.DiffuseColor = [0.7, 0.7, 1.0]


S = OGF.MeshGrob()
S.I.Shapes.create_sphere()
show_Alloy_mesh(S)
