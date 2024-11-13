import numpy as np
import gompy
gom = gompy.interpreter()
OGF = gom.meta_types.OGF

class MeshGrobOps:
    def get_object_bbox(o: OGF.MeshGrob) -> tuple:
        """
        @brief gets the bounding-box of a MeshGrob
        @param[in] o: the MeshGrob
        @return pmin,pmax the bounds, as numpy arrays
        """
        vertices = np.asarray(o.I.Editor.get_points())
        return np.min(vertices,0), np.max(vertices,0)

    def get_object_center(o: OGF.MeshGrob) -> np.ndarray:
        """
        @brief gets the center of a MeshGrob
        @param[in] o: the MeshGrob
        @return the center of the bounding-box of o, as a numpy array
        """
        pmin,pmax = MeshGrobOps.get_object_bbox(o)
        return 0.5*(pmin+pmax)

    def get_object_bbox_diagonal(o: OGF.MeshGrob) -> float:
        """
        @brief gets the bounding-box diagonal of a MeshGrob
        @param[in] o: the MeshGrob
        @return the length of the diagonal of the bounding box of o
        """
        pmin,pmax = MeshGrobOps.get_object_bbox(o)
        return np.linalg.norm(pmax-pmin)

    def translate_object(o: OGF.MeshGrob, T: np.ndarray):
        """
        @brief Applies a translation to object's vertices
        @details Does not call o.update(), it is caller's responsibility
        @param[in,out] o the MeshGrob to be transformed
        @param[in] T the translation vector as a numpy array
        """
        vertices = np.asarray(o.I.Editor.get_points())
        vertices += T

    def transform_object(o: OGF.MeshGrob, xform: np.ndarray):
        """
        @brief Applies a 4x4 homogeneous coord transform to object's vertices
        @details Does not call o.update(), it is caller's responsibility
        @param[in,out] o the MeshGrob to be transformed
        @param[in] xform the 4x4 homogeneous coordinates transform
           as a numpy array
        """
        # if xform is identity, nothing to do
        if np.allclose(xform,np.eye(4)):
            return
        object_vertices = np.asarray(o.I.Editor.get_points())
        vertices = np.c_[  # add a column of 1
            object_vertices, np.ones(object_vertices.shape[0])
        ]
        # transform all the vertices
        vertices = np.matmul(vertices,np.transpose(xform))
        weights  = vertices[:,-1]                 # get 4th column
        weights  = weights[:,np.newaxis]          # make it a Nx1 matrix
        vertices = vertices[:,:-1]                # get the x,y,z coords
        vertices = vertices/weights               # divide the x,y,z coords by w
        # Could be written also in 1 line only (but less legible I think):
        #    vertices = vertices[:,:-1] / vertices[:,-1][:,np.newaxis]
        np.copyto(object_vertices,vertices)       # inject into graphite object

    def set_triangle_mesh(o: OGF.MeshGrob, vrtx: np.ndarray, T: np.ndarray):
        """
        @brief sets a mesh from a vertices array and a triangle array
        @param[out] o: the target mesh
        @param[in] vrtx: an nv*3 array of vertices coordinates
        @param[in] T: an nt*3 array of vertices indices (starting from 0)
        """
        o.clear()
        E = o.I.Editor
        E.create_vertices(vrtx.shape[0])
        E.create_triangles(T.shape[0])
        np.copyto(np.asarray(E.get_points()), vrtx)
        np.copyto(np.asarray(E.get_triangles()), T)
        E.connect_facets()
        o.update()
