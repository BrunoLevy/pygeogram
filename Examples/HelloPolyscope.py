import polyscope as ps
import numpy as np

ps.init()

ps.register_surface_mesh(
 'cube',
  np.array(
  [[ 0, 0, 0 ], 
   [ 0, 0, 1 ], 
   [ 0, 1, 0 ], 
   [ 0, 1, 1 ], 
   [ 1, 0, 0 ], 
   [ 1, 0, 1 ], 
   [ 1, 1, 0 ],
   [ 1, 1, 1 ]]), # cube vertices
  np.array(
  [[ 3, 6, 2 ],
   [ 3, 7, 6 ],
   [ 0, 3, 2 ],
   [ 0, 1, 3 ],
   [ 1, 7, 3 ],
   [ 1, 5, 7 ],
   [ 5, 6, 7 ],
   [ 5, 4, 6 ],
   [ 0, 5, 1 ],
   [ 0, 4, 5 ],
   [ 2, 4, 0 ],
   [ 2, 6, 4 ]]) # triangular facets
)

ps.show()
