##############################
# Bullet Constraints Builder #
##############################
#
# Written within the scope of Inachus FP7 Project (607522):
# "Technological and Methodological Solutions for Integrated
# Wide Area Situation Awareness and Survivor Localisation to
# Support Search and Rescue (USaR) Teams"
# This version is developed at the Laurea University of Applied Sciences, Finland
# Copyright (C) 2015-2017 Kai Kostack
#
# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

################################################################################

import bpy, time
mem = bpy.app.driver_namespace

### Import submodules
from global_vars import *      # Contains global variables
from build_data import *       # Contains build data access functions
from builder_prep import *     # Contains preparation steps functions called by the builder
from builder_setc import *     # Contains constraints settings functions called by the builder

################################################################################

def build():
    
    print("\nStarting...\n")
    time_start = time.time()

    if "RigidBodyWorld" in bpy.data.groups:
    
        bpy.context.tool_settings.mesh_select_mode = True, False, False
        props = bpy.context.window_manager.bcb
        scene = bpy.context.scene
        
        # Display progress bar
        bpy.context.window_manager.progress_begin(0, 100)
        # Leave edit mode
        try: bpy.ops.object.mode_set(mode='OBJECT') 
        except: pass
        
        exData = []

        #########################
        ###### Create new empties
        if not "bcb_objs" in scene.keys():
                
            ###### Create object lists of selected objects
            childObjs = []
            objs, emptyObjs = gatherObjects(scene)
            objsEGrp, objCntInEGrps = createElementGroupIndex(objs)
            
            #############################
            ###### Prepare connection map
            if len(objs) > 1:
                if objCntInEGrps > 1:
                    time_start_connections = time.time()
                    
                    ###### Prepare objects (make unique, apply transforms etc.)
                    prepareObjects(objs)
                    ###### Find connections by vertex pairs
                    #connectsPair, connectsPairDist = findConnectionsByVertexPairs(objs, objsEGrp)
                    ###### Find connections by boundary box intersection and skip connections whose elements are too small and store them for later parenting
                    connectsPair, connectsPairDist = findConnectionsByBoundaryBoxIntersection(objs)
                    ###### Delete connections whose elements are too small and make them parents instead
                    if props.minimumElementSize: connectsPair, connectsPairParent = deleteConnectionsWithTooSmallElementsAndParentThemInstead(objs, connectsPair, connectsPairDist)
                    else: connectsPairParent = []
                    ###### Delete connections with too few connected vertices
                    #connectsPair = deleteConnectionsWithTooFewConnectedVertices(objs, objsEGrp, connectsPair)
                    ###### Calculate contact area for all connections
                    if props.useAccurateArea:
                        connectsGeo, connectsLoc = calculateContactAreaBasedOnBooleansForAll(objs, connectsPair)
                    else:
                        connectsGeo, connectsLoc = calculateContactAreaBasedOnBoundaryBoxesForAll(objs, connectsPair)
                    ###### Delete connections with zero contact area
                    connectsPair, connectsGeo, connectsLoc = deleteConnectionsWithZeroContactArea(objs, connectsPair, connectsGeo, connectsLoc)
                    ###### Create connection data
                    connectsPair, connectsConsts, constsConnect = createConnectionData(objsEGrp, connectsPair)
                    
                    print('-- Time: %0.2f s\n' %(time.time()-time_start_connections))
                    
                    #########################                        
                    ###### Main building part
                    if len(constsConnect) > 0:
                        time_start_building = time.time()
                        
                        ###### Scale elements by custom scale factor and make separate collision object for that
                        applyScale(scene, objs, objsEGrp, childObjs)
                        ###### Bevel elements and make separate collision object for that
                        applyBevel(scene, objs, objsEGrp, childObjs)
                        ###### Create actual parents for too small elements
                        if props.minimumElementSize: makeParentsForTooSmallElementsReal(objs, connectsPairParent)
                        ###### Find and activate first empty layer
                        layersBak = backupLayerSettingsAndActivateNextEmptyLayer(scene)
                        ###### Create empty objects (without any data)
                        if not props.asciiExport:
                            emptyObjs = createEmptyObjs(scene, len(constsConnect))
                        else:
                            emptyObjs = [None for i in range(len(constsConnect))]  # if this is the case emptyObjs is filled with an empty array on None
                        ###### Bundling close empties into clusters, merge locations and count connections per cluster
                        if props.clusterRadius > 0: bundlingEmptyObjsToClusters(connectsLoc, connectsConsts)
                        ###### Add constraint base settings to empties
                        addBaseConstraintSettings(objs, emptyObjs, connectsPair, connectsConsts, connectsLoc, constsConnect, exData)
                        # Restore old layers state
                        scene.update()  # Required to update empty locations before layer switching
                        scene.layers = [bool(q) for q in layersBak]  # Convert array into boolean (required by layers)
                        ###### Store build data in scene
                        if not props.asciiExport: storeBuildDataInScene(scene, objs, objsEGrp, emptyObjs, childObjs, connectsPair, connectsPairParent, connectsLoc, connectsGeo, connectsConsts, constsConnect)
                        
                        print('-- Time: %0.2f s\n' %(time.time()-time_start_building))
                    
                    ###### No connections found   
                    else:
                        print('No connections found. Probably the search distance is too small.')       
                
                ###### No element assigned to element group found
                else:
                    print('Please make sure that at least two mesh objects are assigned to element groups.')       
                    print('Nothing done.')       

            ###### No selected input found   
            else:
                print('Please select at least two mesh objects to connect.')       
                print('Nothing done.')       
       
        ##########################################     
        ###### Update already existing constraints
        if "bcb_objs" in scene.keys() or props.asciiExport:
            
            ###### Store menu config data in scene
            storeConfigDataInScene(scene)
            ###### Get temp data from scene
            if not props.asciiExport: objs, emptyObjs, childObjs, connectsPair, connectsPairParent, connectsLoc, connectsGeo, connectsConsts, constsConnect = getBuildDataFromScene(scene)
            ###### Create fresh element group index to make sure the data is still valid (reordering in menu invalidates it for instance)
            objsEGrp, objCntInEGrps = createElementGroupIndex(objs)
            ###### Store build data in scene
            storeBuildDataInScene(scene, None, objsEGrp, None, None, None, None, None, None, None, None)
                            
            if len(emptyObjs) > 0 and objCntInEGrps > 1:
                ###### Set general rigid body world settings
                initGeneralRigidBodyWorldSettings(scene)
                ###### Find and activate first layer with constraint empty object (required to set constraint locations in setConstraintSettings())
                if not props.asciiExport: layersBak = backupLayerSettingsAndActivateNextLayerWithObj(scene, emptyObjs[0])
                ###### Set constraint settings
                setConstraintSettings(objs, objsEGrp, emptyObjs, connectsPair, connectsGeo, connectsConsts, constsConnect, exData)
                ### Restore old layers state
                if not props.asciiExport:
                    scene.update()  # Required to update empty locations before layer switching
                    scene.layers = [bool(q) for q in layersBak]  # Convert array into boolean (required by layers)
                ###### Calculate mass for all mesh objects
                calculateMass(scene, objs, objsEGrp, childObjs)
                ###### Exporting data into internal ASCII text file
                if props.asciiExport: exportDataToText(exData)
            
                if not props.asciiExport:
                    # Deselect all objects
                    bpy.ops.object.select_all(action='DESELECT')
                    # Select all new constraint empties
                    for emptyObj in emptyObjs: emptyObj.select = 1
                
                print('-- Time total: %0.2f s\n' %(time.time()-time_start))
                print('Constraints:', len(emptyObjs), '| Elements:', len(objs), '| Children:', len(childObjs))
                print('Done.')

            ###### No input found   
            else:
                print('Neither mesh objects to connect nor constraint empties for updating selected.')       
                print('Nothing done.')
                     
    ###### No RigidBodyWorld group found   
    else:
        print('No "RigidBodyWorld" group found in scene. Please create rigid bodies first.')       
        print('Nothing done.')       
        
    # Terminate progress bar
    bpy.context.window_manager.progress_end()