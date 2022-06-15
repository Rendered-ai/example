# Exammple Channel
The Example channel is an educational channel meant to showcase the ability to add 3D models of toys to a scene, apply physics and render images with annotations. 


## Graph Requirements
The following nodes are required to be put in every graph to have the channel run as intended:
- Random Placement: 
- Drop Objects:
- Render: 

## Channel Nodes
The following nodes are available in the channel:
| Name | Inputs | Outputs | Description |
|---|---|---|---|
| Render | Objects of Interest<br />Width (px)<br />Heigth (px) |  | The final node in the graph that is used to render the scene, generating the image and annotation outputs. |
| Drop Objects | Objects<br />Container Generator<br />Floor Generator | Objects of Interest | This node applies physics to the scene that drops the objects. |
| Container | Container Type | Container Generator | This node generates a container with the selected type, the type can be set to \<random\> to randomize which container is selected. |
| Floor | Floor Type | Floor Generator | This node generates a floor with the selected type, the type can be set to \<random\> to randomize which container is selected. |
| Random Placement | Object Generators<br />Number of Objects | Objects | This node applies physics to the scene that drops the objects. |
| Mix Cube |  | Mixed Cube Generator | Generates a mixed Rubik's Cube. |
| Skateboard |  | Skateboard Generator | Generates a skateboad toy. |
| Playdough |  | Play Dough Generator | Generates a Playdough tub. |
| Yo-yo |  | Yoyo Generator | Generates a Yo-yo. |
| Bubbles |  | Bubbles Generator | Generates a Bubbles bottle. |
| Rubik's Cube |  | Rubik's Cube Generator | Generates a solved Rubik's Cube. |
| Color Modifier | Color<br />Generators | Generator | This node modifies the color of the objects, if possible. |
| Weight | Generator<br />Weight | Generator | This node applies a weight to a branch, making it more likely to be selected. |
| Random Integer | low<br />high<br />size | out | Randomly picks an integer between the low and high settings. If a size is selected it will create an array of random integers with that length. |