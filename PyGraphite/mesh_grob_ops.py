import numpy as np
import gompy.types.OGF as OGF

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
        np.copyto(np.asarray(E.get_points()), vrtx)
        if T.shape[0] != 0:
            E.create_triangles(T.shape[0])
            np.copyto(np.asarray(E.get_triangles()), T)
            E.connect_facets()
        o.update()


    def set_parametric_surface(
            o: OGF.MeshGrob,
            F: callable,
            nu: int = 10, nv: int = 10,
            umin: float = 0.0, umax: float = 1.0,
            vmin: float = 0.0, vmax: float = 1.0
    ):
        """
        @brief sets a mesh from a parametric function
        @param[in] F: equation, as a function taking
          two numpy arrays U and V and returning three
          numpy arrays X,Y and Z
        @param[in] nu , nv: number of subdivisions
        @param[in] umin , umax , vmin , vmax: domain bounds
        """
        U = np.linspace(umin, umax, nu)
        V = np.linspace(vmin, vmax, nv)
        V,U = np.meshgrid(V,U)
        X,Y,Z = F(U,V)
        XYZ = np.column_stack((X.flatten(),Y.flatten(),Z.flatten()))

        # create triangles grid

        # https://stackoverflow.com/questions/44934631/
        #   making-grid-triangular-mesh-quickly-with-numpy
        #
        # nu-1 * nv-1 squares
        #                |    two triangles per square
        #                |      |
        #                |      | three vertices per triangle
        #                |      |  /
        #             /-----\   | |
        T = np.empty((nu-1,nv-1,2,3),dtype=np.uint32)

        # 2D vertices indices array
        r = np.arange(nu*nv).reshape(nu,nv)

        # the six vertices of the two triangles
        T[:,:, 0,0] = r[:-1,:-1]     # T0.i        = (u,v)
        T[:,:, 1,0] = r[:-1,1:]      # T1.i        = (u,v+1)
        T[:,:, 0,1] = r[:-1,1:]      # T0.j        = (u,v+1)
        T[:,:, 1,1] = r[1:,1:]       # T1.j        = (u+1,v+1)
        T[:,:, :,2] = r[1:,:-1,None] # T0.k = T1.k = (u+1,v)

        # reshape triangles array
        T = np.reshape(T,(-1,3))

        MeshGrobOps.set_triangle_mesh(o, XYZ, T)

        # if the parameterization winds around (sphere, torus...),
        # we need to glue the vertices
        o.I.Surface.repair_surface()
