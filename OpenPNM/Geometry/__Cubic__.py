"""
module __Cubic__: Generate simple cubic networks
==========================================================

.. warning:: The classes of this module should be loaded through the 'Geometry.__init__.py' file.

"""
#Test
import OpenPNM
import scipy as sp
import numpy as np
import scipy.stats as spst
import scipy.spatial as sptl
import itertools as itr
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
#Test

from __GenericGeometry__ import GenericGeometry

class Cubic(GenericGeometry):
    r"""
    Cubic - Class to create a basic cubic network

    Parameters
    ----------

    loglevel : int
        Level of the logger (10=Debug, 20=INFO, 30=Warning, 40=Error, 50=Critical)

    Examples
    --------
    >>>print 'none yet'

    """

    def __init__(self, **kwargs):
        
        super(Cubic,self).__init__(**kwargs)
        self._logger.debug("Execute constructor")

        #Instantiate pore network object
        self._net=OpenPNM.Network.GenericNetwork()
        
    def generate(self,**params):
        '''
        Create Cubic network. Returns OpenPNM.Network.GenericNetwork() object.

        Parameters
        ----------

        Critical\n
        domain_size : [float,float,float]
            domain_size = [3.0,3.0,3.0] (default)\n
            Bounding cube for internal pore positions\n
        lattice_spacing : [float]
            lattice_spacing = [1.0] (default)\n
            Distance between pore centers\n
        divisions : [int,int,int]
            divisions = [3,3,3]\n
            Number of internal pores in each dimension.\n
            (Optional input. Replaces one of the above.)\n

        Optional\n
        stats_pores : dictionary
            stats_pores = {'name':'weibull_min','shape':1.5,'loc': 6e-6,'scale':2e-5} (default)\n
            Probablity distributions for random pore size assignment\n
        stats_throats : dictionary
            stats_throats = {'name':'weibull_min','shape':1.5,'loc': 6e-6,'scale':2e-5} (default)\n
            Probablity distributions for random throat size assignment\n
        btype : [logical,logical,logical]
            btype = [0,0,0] (default)\n
            Automatically create periodic throats between opposite x, y, or z faces

        Examples:
        ---------

        generate default 100x100x10 cubic network with no periodic boundaries

        >>> import OpenPNM as PNM
        >>> pn=PNM.Geometry.Cubic(domain_size=[100,100,10],lattice_spacing = 1.0)
        '''
        super(Cubic,self).generate(**params)    
        return self._net

    def _generate_setup(self,   domain_size = [],
                                divisions = [],
                                lattice_spacing = [],
                                btype = [0,0,0],
                                **params):
        r"""
        Perform applicable preliminary checks and calculations required for generation
        """
        self._logger.debug("generate_setup: Perform preliminary calculations")
        #Parse the given network size variables
        self._logger.info("Find network dimensions")
        self._btype = btype
        if domain_size and lattice_spacing and not divisions:
            self._Lc = np.float(lattice_spacing[0])
            self._Lx = np.float(domain_size[0])
            self._Ly = np.float(domain_size[1])
            self._Lz = np.float(domain_size[2])
            self._Nx = np.int(self._Lx/self._Lc)
            self._Ny = np.int(self._Ly/self._Lc)
            self._Nz = np.int(self._Lz/self._Lc)
        elif divisions and lattice_spacing and not domain_size:
            self._Lc = np.float(lattice_spacing[0])
            self._Nx = np.int(divisions[0])
            self._Ny = np.int(divisions[1])
            self._Nz = np.int(divisions[2])
            self._Lx = np.float(self._Nx*self._Lc)
            self._Ly = np.float(self._Ny*self._Lc)
            self._Lz = np.float(self._Nz*self._Lc)
        elif domain_size and divisions and not lattice_spacing:
            self._Lc = np.min(np.array(domain_size,dtype=np.float)/np.array(divisions,dtype=np.float))
            self._Nx = np.int(divisions[0])
            self._Ny = np.int(divisions[1])
            self._Nz = np.int(divisions[2])
            self._Lx = np.float(self._Nx*self._Lc)
            self._Ly = np.float(self._Ny*self._Lc)
            self._Lz = np.float(self._Nz*self._Lc)
        elif not domain_size and not divisions and not lattice_spacing:
            self._Lc = np.float(1)
            self._Lx = np.float(3)
            self._Ly = np.float(3)
            self._Lz = np.float(3)
            self._Nx = np.int(self._Lx/self._Lc)
            self._Ny = np.int(self._Ly/self._Lc)
            self._Nz = np.int(self._Lz/self._Lc)
        else:
            self._logger.error("Exactly two of domain_size, divisions and lattice_spacing must be given")
            raise Exception('Exactly two of domain_size, divisions and lattice_spacing must be given')

    def _generate_pores(self):
        r"""
        Generate the pores (coordinates, numbering and types)
        """
        self._logger.info("generate_pores: Create specified number of pores")
        Nx = self._Nx
        Ny = self._Ny
        Nz = self._Nz
        Lc = self._Lc
        Np = Nx*Ny*Nz
        ind = np.arange(0,Np)
        self._net.pore_properties['coords'] = Lc/2+Lc*np.array(np.unravel_index(ind, dims=(Nx, Ny, Nz), order='F'),dtype=np.float).T
        self._net.pore_properties['numbering'] = ind
        self._net.pore_properties['type']= np.zeros((Np,),dtype=np.int8)

        self._logger.debug("generate_pores: End of method")

    def _generate_throats(self):
        r"""
        Generate the throats (connections, numbering and types)
        """
        self._logger.info("generate_throats: Define connections between pores")

        Nx = self._Nx
        Ny = self._Ny
        Nz = self._Nz
        Np = Nx*Ny*Nz
        ind = np.arange(0,Np)

        #Generate throats based on pattern of the adjacency matrix
        tpore1_1 = ind[(ind%Nx)<(Nx-1)]
        tpore2_1 = tpore1_1 + 1
        tpore1_2 = ind[(ind%(Nx*Ny))<(Nx*(Ny-1))]
        tpore2_2 = tpore1_2 + Nx
        tpore1_3 = ind[(ind%Np)<(Nx*Ny*(Nz-1))]
        tpore2_3 = tpore1_3 + Nx*Ny
        tpore1 = np.hstack((tpore1_1,tpore1_2,tpore1_3))
        tpore2 = np.hstack((tpore2_1,tpore2_2,tpore2_3))
        connections = np.vstack((tpore1,tpore2)).T
        connections = connections[np.lexsort((connections[:, 1], connections[:, 0]))]
        self._net.throat_properties['connections'] = connections
        self._net.throat_properties['type'] = np.zeros(np.shape(tpore1),dtype=np.int8)
        self._net.throat_properties['numbering'] = np.arange(0,np.shape(tpore1)[0])
        
        self._logger.debug("generate_throats: End of method")









    def _add_boundary_throat_type(self,net):
        throat_type = np.zeros(len(net.throat_properties['type']))
        for i in range(3):
            bound_1 = net.pore_properties['coords'][:,i].min()
            bound_2 = net.pore_properties['coords'][:,i].max()
            bound_ind_1 = np.where(net.pore_properties['coords'][:,i] == bound_1)
            bound_ind_2 = np.where(net.pore_properties['coords'][:,i] == bound_2)
            throat_type[bound_ind_1] = i+1
            throat_type[bound_ind_2] = 6-i
            self._temp_throat_type = throat_type
    
    
    
    def _add_boundary_pore_type(self,net):
        pore_type = np.zeros(len(net.pore_properties['type']))
        for i in range(3):
            bound_1 = net.pore_properties['coords'][:,i].min()
            bound_2 = net.pore_properties['coords'][:,i].max()
            bound_ind_1 = np.where(net.pore_properties['coords'][:,i] == bound_1)
            bound_ind_2 = np.where(net.pore_properties['coords'][:,i] == bound_2)
            pore_type[bound_ind_1] = i+1
            pore_type[bound_ind_2] = 6-i
            self._temp_pore_type = pore_type





    def _generate_boundaries(self,net,**params):

        self._logger.info("generate_boundaries: Define edge points of the pore network and stitch them on")
        self._generate_setup(**params)
        Lc = self._Lc
        params['divisions'] = [self._Nx, self._Ny, self._Nz]
        temp_divisions = sp.copy(params['divisions']).tolist()
        
        for i in range(0,6):
            params['divisions'] = temp_divisions
            temp_divisions = sp.copy(params['divisions']).tolist()
            params['divisions'][i%3] = 1
            edge_net = super(Cubic, self).generate(**params)
            displacement = [0,0,0]
            if i < 3:
                displacement[i%3] = net.pore_properties['coords'][:,i%3].max() + 0.5*Lc
            else:
                displacement[i%3] = -1*(net.pore_properties['coords'][:,i%3].min() + 0.5*Lc)
            self.translate_coordinates(edge_net,displacement)
            self.stitch_network(net,edge_net,edge = i+1,stitch_nets = 0)

        self._stitch_throats(net)
        self._add_boundary_throat_type(net)
        net.pore_properties['type'] = self._temp_pore_type
        self._add_boundary_pore_type(net)
        net.throat_properties['type'] = self._temp_throat_type
        
        return net
        self._logger.debug("generate_boundaries: End of method")







    def stitch_network(self,net1,net2,edge = 0, stitch_nets = 1, stitch_side = []):
        r"""
        Stitch two networks together

        Parameters
        ----------
        net1 : OpenPNM Network Object
            The network that is stiched to

        net2 : OpenPNM Network Object
            The network that is stitched

        edge : default value of 0. This changed if you are adding boundaries to an existing network.

        stitch_nets : default value of 1. This assumes you are stitching 2 separately generated networks together. If the value
            is changed to a value of 0, you don't append the throats of the stitched network because you are adding boundary pores.

        stitch_side : string (optional)
            When given, this flag moves net2 into position automatically

        """
        net2.pore_properties['numbering']   = len(net1.pore_properties['numbering']) + net2.pore_properties['numbering']
        net1.pore_properties['numbering']   = sp.concatenate((net1.pore_properties['numbering'],net2.pore_properties['numbering']),axis=0)
        net1.pore_properties['volume']      = sp.concatenate((net1.pore_properties['volume'],net2.pore_properties['volume']),axis = 0)
        net1.pore_properties['seed']        = sp.concatenate((net1.pore_properties['seed'],net2.pore_properties['seed']),axis = 0)            
        net1.pore_properties['diameter']    = sp.concatenate((net1.pore_properties['diameter'],net2.pore_properties['diameter']),axis = 0)
        
        if stitch_nets:
            #if ~stitch_size:
                #stitch in place
            if stitch_side == 'left':
                def_translate = net1.pore_properties['coords'][:,0].max()+net1.pore_properties['coords'][:,0].min()
                OpenPNM.Geometry.GenericGeometry.translate_coordinates(net2,displacement=[def_translate,0,0])
            elif stitch_side == 'right':
                def_translate = net1.pore_properties['coords'][:,0].max()+net1.pore_properties['coords'][:,0].min()
                OpenPNM.Geometry.GenericGeometry.translate_coordinates(net2,displacement=[-1*def_translate,0,0])
            elif stitch_side == 'back':
                def_translate = net1.pore_properties['coords'][:,1].max()+net1.pore_properties['coords'][:,1].min()
                OpenPNM.Geometry.GenericGeometry.translate_coordinates(net2,displacement=[0,def_translate,0])
            elif stitch_side == 'front':
                def_translate = net1.pore_properties['coords'][:,1].max()+net1.pore_properties['coords'][:,1].min()
                OpenPNM.Geometry.GenericGeometry.translate_coordinates(net2,displacement=[0,-1*def_translate,0])
            elif stitch_side == 'top':
                def_translate = net1.pore_properties['coords'][:,2].max()+net1.pore_properties['coords'][:,2].min()
                OpenPNM.Geometry.GenericGeometry.translate_coordinates(net2,displacement=[0,0,def_translate])
            elif stitch_side == 'bottom':
                def_translate = net1.pore_properties['coords'][:,2].max()+net1.pore_properties['coords'][:,2].min()
                OpenPNM.Geometry.GenericGeometry.translate_coordinates(net2,displacement=[0,0,-1*def_translate])

        net1.pore_properties['coords']      = sp.concatenate((net1.pore_properties['coords'],net2.pore_properties['coords']),axis = 0)
        net1.pore_properties['type']        = sp.concatenate((net1.pore_properties['type'],net2.pore_properties['type']),axis = 0)
        net2.throat_properties['numbering'] = len(net1.throat_properties['numbering']) + net2.throat_properties['numbering']
        net1.throat_properties['numbering'] = sp.concatenate((net1.throat_properties['numbering'],net2.throat_properties['numbering']),axis=0)
        net1.throat_properties['seed']      = sp.concatenate((net1.throat_properties['seed'],net2.throat_properties['seed']),axis=0)
        net1.throat_properties['diameter']  = sp.concatenate((net1.throat_properties['diameter'],net2.throat_properties['diameter']),axis=0)
        net1.throat_properties['volume']    = sp.concatenate((net1.throat_properties['volume'],net2.throat_properties['volume']),axis=0)
        net1.throat_properties['length']    = sp.concatenate((net1.throat_properties['length'],net2.throat_properties['length']),axis=0)







    def _stitch_throats(self,net):
        r"""
        Stitch two networks together OR adds the boundary throats to an existing network

        Parameters
        ----------
        net : OpenPNM Network Object
            The network that is stiched, whos throats are being added.

        """

        pts = net.pore_properties['coords']
        tri = sptl.Delaunay(pts)

        adj_mat = (sp.zeros((len(pts),len(pts)))-1).copy()
        dist_comb = list(itr.combinations_with_replacement(range(4),2))

        for i in range(len(tri.simplices)):
            for j in range(len(dist_comb)):
                point_1 = tri.simplices[i,dist_comb[j][0]]
                point_2 = tri.simplices[i,dist_comb[j][1]]
                coords_1 = tri.points[point_1]
                coords_2 = tri.points[point_2]
                adj_mat[point_1,point_2] = self._net.fastest_calc_dist(coords_1,coords_2) #move off of network

        #Begin removing undesired connections based on their length
        ind = np.ma.where(adj_mat>0)
        I = ind[:][0].tolist()
        J = ind[:][1].tolist()
        V = adj_mat[I,J]
        masked = np.where((adj_mat < (V.min() + .001)) & (adj_mat > 0))
        connections = np.zeros((len(masked[0]),2),np.int)

        for i in range(len(masked[0])):
            connections[i,0] = masked[0][i]
            connections[i,1] = masked[1][i]

        net.throat_properties['connections'] =  connections
        net.throat_properties['numbering'] = np.arange(0,len(connections[:,0]))
        net.throat_properties['type'] = np.zeros(len(connections[:,0]),dtype=np.int8)
        net.throat_properties['seed'] = sp.amin(net.pore_properties['seed'][net.throat_properties['connections']],1)
        
if __name__ == '__main__':
    test=Cubic(loggername='TestCubic')
    pn = test.generate(lattice_spacing=1.0,domain_size=[3,3,3], btype=[1,1,0])
