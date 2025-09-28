
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

def mkVtkIdList(it):
    vil = vtkIdList()
    for i in it:
        vil.InsertNextId(int(i))
    return vil


def create_cube():
    # x = array of 8 3-tuples of float representing the vertices of a cube:
    x = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0),
         (0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0)]

    # pts = array of 6 4-tuples of vtkIdType (int) representing the faces
    #     of the cube in terms of the above vertices
    pts = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
           (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]

    # We'll create the building blocks of polydata including data attributes.
    cube = vtkPolyData()
    points = vtkPoints()
    polys = vtkCellArray()
    scalars = vtkFloatArray()

    # Load the point, cell, and data attributes.
    for i, xi in enumerate(x):
        points.InsertPoint(i, xi)
    for pt in pts:
        polys.InsertNextCell(mkVtkIdList(pt))
    for i, _ in enumerate(x):
        scalars.InsertTuple1(i, i)

    # We now assign the pieces to the vtkPolyData.
    cube.SetPoints(points)
    cube.SetPolys(polys)
    cube.GetPointData().SetScalars(scalars)

    tp = paraview.simple.TrivialProducer()
    tp.GetClientSideObject().SetOutput(cube)
    display = paraview.simple.Show(tp)
    display.Representation = 'Surface'
    display.DiffuseColor = [0.7, 0.7, 1.0]


create_cube()
