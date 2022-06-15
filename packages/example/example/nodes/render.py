# Copyright 2019-2022 DADoES, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the root directory in the "LICENSE" file or at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import bpy
import anatools.lib.context as ctx
from anatools.lib.node import Node
from anatools.lib.scene import AnaScene
import logging
import imageio
import math
import os
import numpy
import glob

logger = logging.getLogger(__name__)


class RenderNode(Node):
    """
    A class to represent a the Render node, a node that renders an image of the given scene.
    Executing the Render node creates an image, annotation, and metadata file.
    """

    def exec(self):
        """Execute node"""
        #return {}  # testing the time to bake the physics
        logger.info("Executing {}".format(self.name))

        try:
            #We do not expect more than one DropObjects node to be ported to here, but the input is still a list.
            objects = self.inputs["Objects of Interest"][0]

            scn = bpy.context.scene

            bpy.ops.object.visual_transform_apply()

            sizeMax = 3000
            scn.render.resolution_x = min(sizeMax, int(self.inputs["Width (px)"][0]))
            scn.render.resolution_y = min(sizeMax, int(self.inputs["Height (px)"][0]))


            #Let's add a lamp...This could be done in a separate node if desired.
            bpy.context.scene.world.light_settings.use_ambient_occlusion = True

            lamp_data = bpy.data.lights.new("light",type='SPOT')
            lamp_data.energy = 10
            lamp_object = bpy.data.objects.new("light 1",lamp_data)
            lamp_object.location = (0.0, 0.0, 1.0)
            scn.collection.objects.link(lamp_object)

            cam1 = bpy.data.cameras.new("Camera 1")
            cam_obj1 = bpy.data.objects.new("Camera 1", cam1)
            max_height = 0.55
            height = ctx.random.uniform(0.25, max_height)
            y = math.sqrt(max_height**2 - height**2)
            cam_obj1.location = (.15, y, height)

            scn.collection.objects.link(cam_obj1)

            scn.camera = cam_obj1

            camera_constraint = cam_obj1.constraints.new(type='TRACK_TO')
            floor = [o for o in scn.objects if 'Plane' in o.name][0]
            camera_constraint.target = floor

            #Initialize an AnaScene.  This configures the Blender compositor and provides object annotations and metadata.
            #To create an AnaScene we need to send a blender scene and a view layer for annotations
            sensor_name = 'RGBCamera'
            scene = AnaScene(
                blender_scene=scn,
                annotation_view_layer=bpy.context.view_layer,
                objects=objects,
                sensor_name=sensor_name)

            #Add denoise node to compositor
            s = bpy.data.scenes[ctx.channel.name]
            c_rl = s.node_tree.nodes['Render Layers']
            c_c = s.node_tree.nodes['Composite']
            c_dn = s.node_tree.nodes.new('CompositorNodeDenoise')
            s.node_tree.nodes.remove(s.node_tree.nodes['imgout'])
            c_of = s.node_tree.nodes.new('CompositorNodeOutputFile')
            c_of.base_path = os.path.join(ctx.output,'images')
            c_of.file_slots.clear()
            c_of.file_slots.new(f'{ctx.interp_num:010}-#-{sensor_name}.png')
            s.node_tree.links.new(c_rl.outputs[0], c_dn.inputs[0])
            s.node_tree.links.new(c_dn.outputs[0], c_c.inputs[0])
            s.node_tree.links.new(c_dn.outputs[0], c_of.inputs[0])
                        
            #OK. Now it's time to render.
            if ctx.preview:
                logger.info("LOW RES Render for Preview")
                render(resolution='preview')
                imgfilename = f"{ctx.interp_num:010}-{scn.frame_current}-{sensor_name}.png"
                preview = imageio.imread(os.path.join(ctx.output,'images',imgfilename))
                imageio.imsave(os.path.join(ctx.output,'preview.png'), preview)
                return{}
            else:
                #bpy.ops.wm.save_as_mainfile(filepath="scene4render.blend")
                render()

            #Prepare for annotataions: Remove link to image output file, update objects, (re)write masks
            s = bpy.data.scenes[ctx.channel.name]
            c_of = s.node_tree.nodes['File Output']
            c_of.file_slots.clear()
            for obj in objects:
                obj.setup_mask()
            render(resolution='masks')
            c_of.file_slots.new(f'{ctx.interp_num:010}-#-{sensor_name}.png')
            s.node_tree.links.new(c_dn.outputs[0], c_of.inputs[0])

            calculate_obstruction = self.inputs["Calculate Obstruction"][0]
            
            if calculate_obstruction == 'F':
                # Create annotations 
                scene.write_ana_annotations()
                scene.write_ana_metadata()
                return {}
            
            #Render masks for each object.
            #only render a mask file for objects in the image

            #Unlink all the object masks in the compositor
            links = scn.node_tree.links
            masknodes = [node for node in scn.node_tree.nodes if node.name.split('_')[-1]=='mask']
            masklinks = {}
            for masknode in masknodes:
                masklinks[masknode.index] = {
                    'masknode': masknode,
                    'socketinput': masknode.outputs[0].links[0].to_socket
                }
                links.remove(masknode.outputs[0].links[0])
            #Unlink the image from the compositor
            for link in scn.node_tree.nodes['Render Layers'].outputs['Image'].links:
                links.remove(link)

            masktemplate = os.path.join(scene.maskout.base_path,
                                        scene.maskout.file_slots[0].path + '.' + scene.maskout.format.file_format.lower())

            #Only render a mask file for objects in the image
            compositemaskfile = masktemplate.replace('#', str(scn.frame_current))
            compimg = imageio.imread(compositemaskfile)
            allmasks = compimg[numpy.nonzero(compimg)]
            renderedobjectidxs = numpy.unique(allmasks)
            renderedobjects = [obj for obj in objects if obj.instance in renderedobjectidxs]

            #Hide all but a single object and render a mask
            for obj in objects:
                obj.root.hide_render = True
                if obj not in renderedobjects:
                    obj.rendered = False

            imgpath = scene.imgout.file_slots[0].path
            maskpath = scene.maskout.file_slots[0].path
            for obj in renderedobjects:
                obj.solo_mask_id = f'obj{obj.instance:03}'
                scene.maskout.file_slots[0].path = '{}-{}'.format(maskpath, obj.solo_mask_id)
                scene.imgout.file_slots[0].path = '{}-{}'.format(imgpath, obj.solo_mask_id)

                obj.root.hide_render = False

                # link the ID mask node to it's divide node
                masknode = masklinks[obj.instance]['masknode']
                socketinput = masklinks[obj.instance]['socketinput']
                links.new(masknode.outputs['Alpha'], socketinput)

                render(resolution='low')

                # rehide object
                obj.root.hide_render = True
                links.remove(masknode.outputs[0].links[0])

            #Create annotations
            scene.write_ana_annotations(calculate_obstruction=calculate_obstruction)
            scene.write_ana_metadata()

            print("Number Objects Rendered: {}".format(len([o for o in objects if o.rendered])))

            #Clean up extra rendered files
            maskpattern = os.path.join(scene.maskout.base_path, maskpath.replace('#', str(scn.frame_current)))
            for filepath in glob.glob('{}-*'.format(maskpattern)):
                os.remove(filepath)
            imgpattern = os.path.join(scene.imgout.base_path, imgpath.replace('#', str(scn.frame_current)))
            for filepath in glob.glob('{}-*'.format(imgpattern)):
                os.remove(filepath)

        except Exception as e:
            logger.error("{} in \"{}\": \"{}\"".format(type(e).__name__, type(self).__name__, e).replace("\n", ""))
            raise

        return {}


def render(resolution='high'):
    # The render patch size, 256 is best for GPU
    bpy.context.scene.render.tile_x = 256
    bpy.context.scene.render.tile_y = 256

    if resolution == 'preview':
        if bpy.context.scene.render.resolution_x >1000:
            # For speed, set the resolution to a common multiple of the tile size
            bpy.context.scene.render.resolution_x = 640
            bpy.context.scene.render.resolution_y = 384
        bpy.context.scene.render.tile_x = 64
        bpy.context.scene.render.tile_y = 64

        bpy.context.scene.cycles.samples = 8
        bpy.context.scene.cycles.max_bounces = 6

    elif resolution == 'high':
        # Higher samples and bounces diminishes speed for higher quality images
        bpy.context.scene.cycles.samples = 15
        bpy.context.scene.cycles.max_bounces = 12

    else: # masks
        bpy.context.scene.cycles.samples = 1
        bpy.context.scene.cycles.max_bounces = 1

    bpy.ops.render.render('INVOKE_DEFAULT')
