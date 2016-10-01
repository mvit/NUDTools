bl_info = {
    "name": "Smash 4 NUD (.nud)",
    "author": "mvit, thanks to Kalomaze, Pannash and InTheBeef",
    "version": (0,1,0),
    "blender": (2,6,9),
    "location": "File > Export > Super Smash Bros. for Wii U Model (.nud)",
    "warning": "EXPERIMENTAL, MAKE SURE EVERY OBJECT HAS BEEN TRIANGULATED, UV MAPPED AND HAS A COLOR LAYER",
    "category": "Export"
}

import bpy
import struct
import re

#Thanks to smb for this function
def compress(float32):
        F16_EXPONENT_BITS = 0x1F
        F16_EXPONENT_SHIFT = 10
        F16_EXPONENT_BIAS = 15
        F16_MANTISSA_BITS = 0x3ff
        F16_MANTISSA_SHIFT =  (23 - F16_EXPONENT_SHIFT)
        F16_MAX_EXPONENT =  (F16_EXPONENT_BITS << F16_EXPONENT_SHIFT)
        
        a = struct.unpack('>I', struct.pack('>f',float32))
        b = hex(a[0])

        f32 = int(b,16)
        f16 = 0
        sign = (f32 >> 16) & 0x8000
        exponent = ((f32 >> 23) & 0xff) - 127
        mantissa = f32 & 0x007fffff

        if exponent == 128:
            f16 = sign | F16_MAX_EXPONENT
            if mantissa:
                f16 |= (mantissa & F16_MANTISSA_BITS)
        elif exponent > 15:
            f16 = sign | F16_MAX_EXPONENT
        elif exponent > -15:
            exponent += F16_EXPONENT_BIAS
            mantissa >>= F16_MANTISSA_SHIFT
            f16 = sign | exponent << F16_EXPONENT_SHIFT | mantissa
        else:
            f16 = sign
        return f16

def write_delayed(ctx, file, name, fmt, default):
    if name in ctx['delayed']:
        raise Exception('Delayed tag {} is already allocated'.format(name))
    ctx['delayed'][name] = (file.tell(), fmt)
    write_struct_to_file(file, fmt, default)

def resolve_delayed(ctx, file, name, value):
    oldpos = file.tell()
    position, fmt = ctx['delayed'][name]
    file.seek(position)
    write_struct_to_file(file, fmt, value)
    file.seek(oldpos)
    del ctx['delayed'][name]

def write_struct_to_file(file, fmt, data):
    file.write(struct.pack(fmt, *data))

nums = re.compile(r'\.\d{3}$')
def cut_name(name):
    if nums.findall(name):
        return name[:-4]  # cut off blender's .001 .002 etc
    return name

def bone_to_index(str):
    print(str)
    idx = [int(s) for s in str.split() if s.isdigit()]
    print(idx)
    print(idx[0] + 2)
    return int(idx[0] + 2)

def group_to_bones(ctx, groups):
    new_groups = []

    for i in range(len(groups)):
        group_name = ctx['groups'][groups[i][0]].name
        print(group_name)
        new_groups. append((bone_to_index(group_name), groups[i][1]))
    
    print(new_groups)
    return new_groups

def prepare_name(name):
    if(len(name) >= 16):
        bname = name.ljust(32, u"\u0000")
    else:
        bname = name.ljust(16, u"\u0000")
    bname = bytes(bname, 'ascii')
    return bname

def write_names(ctx, i, file):
    resolve_delayed(ctx, file, 'obj{}name'.format(i), (file.tell() - ctx['nameoffset'],))
    name = prepare_name(ctx['objnames'][i])
    file.write(name)
    for mats in range(10):
        print(hex(file.tell() - ctx['nameoffset']))
        resolve_delayed(ctx, file, 'mat{}name'.format(mats + 1 + (i*10)), (file.tell() - ctx['nameoffset'],))
        matname = prepare_name(ctx['matnames'][mats + (i*10)])
        file.write(matname)

def get_name_count(ctx):
    return len(ctx['matnames'])

def add_padding(ctx, i, file):
    write_struct_to_file(file, '>B', (0,))

def write_n_items(ctx, file, n, func):
    for i in range(n):
        func(ctx, i, file)

def write_obj_tag(ctx, i, file):
    #Write gunk
    write_struct_to_file(file, '>IIII', (0xC0CE5607,0x40EC1565, 0x408C62F6, 0x40C455A4))
    write_struct_to_file(file, '>IIII', (0xC0CE5607,0x40EC1565, 0x408C62F6, 0x00000000))
    
    #Write tag
    #Name pointer
    write_delayed(ctx, file, 'obj{}name'.format(i), '>l', (0,))
    
    #idA, bind, pcount
    write_struct_to_file(file, '>l', (0x0004,))
    
    write_delayed(ctx, file, 'obj{}bind'.format(i), '>H', (0xFFFF,))
    
    write_struct_to_file(file, '>H', (0x1,))
    
    ctx['polytagcount'] += 1
    
    #write polytag location
    write_delayed(ctx, file, 'obj{}_ptag'.format(i), '>l', (0,))

def write_poly_tag(ctx, i, file):
    resolve_delayed(ctx, file, 'obj{}_ptag'.format(i), (file.tell(),))
    
    write_delayed(ctx, file, 'poly{}_facestart'.format(i), '>l', (0,))
    write_delayed(ctx, file, 'poly{}_uvstart'.format(i), '>l', (0,))
    write_delayed(ctx, file, 'poly{}_vertstart'.format(i), '>l', (0,))
    
    write_delayed(ctx, file, 'poly{}_vertcount'.format(i), '>H', (0,))
    
    if(ctx['rigged'] == True):
        write_struct_to_file(file,'>BB', (0x46, 0x12))
    else:
        write_struct_to_file(file,'>BB', (0x06, 0x12))

    write_delayed(ctx, file, 'poly{}_tex1'.format(i), '>l', (0,))
    write_struct_to_file(file, '>lll', (0x0,0x0,0x0))
    
    write_delayed(ctx, file, 'poly{}_fcount'.format(i), '>H', (0,))
    write_struct_to_file(file, '>B', (0x40,))
    write_delayed(ctx, file, 'poly{}_pflag'.format(i), '>B',  (0x04,))
    
    write_struct_to_file(file, '>lll', (0x0,0x0,0x0))

def write_materials(ctx, i, file):
    resolve_delayed(ctx, file, 'poly{}_tex1'.format(i), (file.tell(),))
    write_material_header(ctx, 1, file)

    write_material_texture(ctx, 1, file)
    
    write_material_parameters(ctx, 1, file)
    
def write_material_header(ctx, i, file):
    write_struct_to_file(file, '>IlHHHH', (0x9a011063,0x0,0x1,0x1,0x1,0x0204))
    write_struct_to_file(file, '>HHfff', (0x0080, 0x0405, 0x0,0x0,0x0))

def write_material_texture(ctx, i, file):
    write_struct_to_file(file, '>llHHBBBB', (0x40450400, 0x0, 0x0, 0x0000, 0x03, 0x03, 0x03, 0x01))
    write_struct_to_file(file, '>HHl', (0x0600, 0x0000,0x0))

def write_material_parameters(ctx, i, file):
    ctx['matnames'].append("NU_colorSamplerUV")
    write_struct_to_file(file, '>l', (0x20,))
    write_delayed(ctx, file, 'mat{}name'.format(get_name_count(ctx)), '>l', (0,))
    write_struct_to_file(file, '>llffff', (0x4,0x0,0x0,0x0,0x0,0x0))
    
    ctx['matnames'].append("NU_fresnelColor")
    write_struct_to_file(file, '>l', (0x20,))
    write_delayed(ctx, file, 'mat{}name'.format(get_name_count(ctx)), '>l', (0,))
    write_struct_to_file(file, '>llffff', (0x4,0x0,0x0,0x0,0x0,0x0))
    
    ctx['matnames'].append("NU_blinkColor")
    write_struct_to_file(file, '>l', (0x20,))
    write_delayed(ctx, file, 'mat{}name'.format(get_name_count(ctx)), '>l', (0,))
    write_struct_to_file(file, '>llffff', (0x4,0x0,0x0,0x0,0x0,0x0))
    
    ctx['matnames'].append("NU_specularColor")
    write_struct_to_file(file, '>l', (0x20,))
    write_delayed(ctx, file, 'mat{}name'.format(get_name_count(ctx)), '>l', (0,))
    write_struct_to_file(file, '>llffff', (0x4,0x0,0x0,0x0,0x0,0x0))
    
    ctx['matnames'].append("NU_aoMinGain")
    write_struct_to_file(file, '>l', (0x20,))
    write_delayed(ctx, file, 'mat{}name'.format(get_name_count(ctx)), '>l', (0,))
    write_struct_to_file(file, '>llffff', (0x4,0x0,0x0,0x0,0x0,0x0))
    
    ctx['matnames'].append("NU_lightMapColorOffset")
    write_struct_to_file(file, '>l', (0x20,))
    write_delayed(ctx, file, 'mat{}name'.format(get_name_count(ctx)), '>l', (0,))
    write_struct_to_file(file, '>llffff', (0x4,0x0,0x0,0x0,0x0,0x0))
    
    ctx['matnames'].append("NU_specularParams")
    write_struct_to_file(file, '>l', (0x20,))
    write_delayed(ctx, file, 'mat{}name'.format(get_name_count(ctx)), '>l', (0,))
    write_struct_to_file(file, '>llffff', (0x4,0x0,0x0,0x0,0x0,0x0))
    
    ctx['matnames'].append("NU_fresnelParams")
    write_struct_to_file(file, '>l', (0x20,))
    write_delayed(ctx, file, 'mat{}name'.format(get_name_count(ctx)), '>l', (0,))
    write_struct_to_file(file, '>llffff', (0x4,0x0,0x0,0x0,0x0,0x0))
    
    ctx['matnames'].append("NU_alphaBlendParams")
    write_struct_to_file(file, '>l', (0x20,))
    write_delayed(ctx, file, 'mat{}name'.format(get_name_count(ctx)), '>l', (0,))
    write_struct_to_file(file, '>llffff', (0x4,0x0,0x0,0x0,0x0,0x0))
    
    ctx['matnames'].append("NU_materialHash")
    write_struct_to_file(file, '>l', (0x0,))
    write_delayed(ctx, file, 'mat{}name'.format(get_name_count(ctx)), '>l', (0,))
    write_struct_to_file(file, '>llffff', (0x4,0x0,0x39d4c11e,0x0,0x0,0x0))

def write_tri(ctx, i, file):
    assert ctx['mesh'].polygons[i].loop_total == 3
    start = ctx['mesh'].polygons[i].loop_start
    a, b, c = (ctx['loop_to_vert'][j] for j in range(start, start + 3))  # swapped c/b
    write_struct_to_file(file, '>HHH', (a, b, c))

def write_tris(ctx, i, file):
    ctx['mesh'] = ctx['obj'][i].data

    gather_loops(ctx)

    resolve_delayed(ctx, file, 'poly{}_fcount'.format(i), (len(ctx['mesh'].polygons) * 3,))
    resolve_delayed(ctx, file, 'poly{}_facestart'.format(i), (file.tell() - ctx['trioffset'],))
    write_n_items(ctx, file, len(ctx['mesh'].polygons), write_tri)

def write_vert(ctx, i, file):
    loop_id = ctx['vert_to_loop'][i]
    vert_id = ctx['mesh'].loops[loop_id].vertex_index
    
    vert = ctx['mesh'].vertices[vert_id]
    coord = vert.co
    normal = vert.normal
    groups = vert.groups

    idx = []

    for g in groups:
         idx.append((g.group, int(g.weight*255)))

    new = group_to_bones(ctx, idx)

    if (len(new) < 4):
         addverts = 4 - len(new)
         for i in range(addverts):
             new.append((0x2,0))

    print(new)
    
    nx = compress(normal.x)
    ny = compress(normal.y)
    nz = compress(normal.z)
    
    write_struct_to_file(file, '>fffHHHH', (coord.x, coord.z, coord.y*-1, nx, nz, ny, 0x3C00))
    write_struct_to_file(file, '>BBBB', (new[0][0], new[1][0], new[2][0], new[3][0]))
    write_struct_to_file(file, '>BBBB', (new[0][1], new[1][1], new[2][1], new[3][1]))

def write_verts(ctx, i, file):
    print(ctx['obj'][i].name)
    
    ctx['groups'] = ctx['obj'][i].vertex_groups
    
    ctx['mesh'] = ctx['obj'][i].data
    
    gather_loops(ctx)

    resolve_delayed(ctx, file, 'poly{}_vertcount'.format(i), (len(ctx['vert_to_loop']),))
    resolve_delayed(ctx, file, 'poly{}_vertstart'.format(i), (file.tell() - ctx['vertoffset'],))
    #if (len(ctx['groups']) == 1):
      #resolve_delayed(ctx, file, 'obj{}_singlebind'.format(i), (group_to_bones(ctx['groups'][0])[0],))
    #else:
    resolve_delayed(ctx, file, 'poly{}_pflag'.format(i), (0x04,))
    write_n_items(ctx, file, len(ctx['vert_to_loop']), write_vert)

def write_static_vert(ctx, i, file):
    loop_id = ctx['vert_to_loop'][i]
    vert_id = ctx['mesh'].loops[loop_id].vertex_index
    
    vert = ctx['mesh'].vertices[vert_id]
    coord = vert.co
    normal = vert.normal
    
    nx = compress(normal.x)
    ny = compress(normal.y)
    nz = compress(normal.z)

    uv = ctx['mesh'].uv_layers.active.data[loop_id].uv
    u = compress (uv[0])
    v = compress (uv[1])
    
    col = ctx['mesh'].vertex_colors.active.data[loop_id].color
    
    write_struct_to_file(file, '>fffHHHH', (coord.x, coord.z, coord.y * -1, nx, nz, ny, 0x3C00))
    write_struct_to_file(file, '>BBBB', (int(col[0]*255), int(col[1]*255), int(col[2]*255), 0xFF))
    write_struct_to_file(file, '>HH', (u,v))

def write_static_verts(ctx, i, file):
    
    ctx['mesh'] = ctx['obj'][i].data
    
    gather_loops(ctx)

    resolve_delayed(ctx, file, 'poly{}_vertcount'.format(i), (len(ctx['vert_to_loop']),))
    resolve_delayed(ctx, file, 'poly{}_uvstart'.format(i), (file.tell() - ctx['vertoffset'],))

    write_n_items(ctx, file, len(ctx['vert_to_loop']), write_static_vert)

def gather_loops(ctx):
    vert_to_loop = []
    loop_to_vert = []
    index = {}
    
    for i, loop in enumerate(ctx['mesh'].loops):
        key = (loop.vertex_index, tuple(loop.normal))
        vid = index.get(key, None)
        if vid is None:
            vid = len(vert_to_loop)
            index[key] = vid
            vert_to_loop.append(i)
        loop_to_vert.append(vid)
    ctx['vert_to_loop'] = vert_to_loop
    ctx['loop_to_vert'] = loop_to_vert

def write_uvcol(ctx, i, file):
    idx = ctx['vert_to_loop'][i]

    uv = ctx['mesh'].uv_layers.active.data[idx].uv
    u = compress (uv[0])
    v = compress (uv[1])
    
    col = ctx['mesh'].vertex_colors.active.data[idx].color
    
    write_struct_to_file(file, '>BBBB', (int(col[0]*255), int(col[1]*255), int(col[2]*255), 0xFF))
    #write_struct_to_file(file, '>BBBB', (0xFF, 0xFF, 0xFF, 0xFF))
    write_struct_to_file(file, '>HH', (u,v))

def write_uvcols(ctx, i, file):
    ctx['mesh'] = ctx['obj'][i].data
    resolve_delayed(ctx, file, 'poly{}_uvstart'.format(i), (file.tell() - ctx['uvoffset'],))

    gather_loops(ctx)

    write_n_items(ctx, file, len(ctx['vert_to_loop']), write_uvcol)

def writeNUD(context, filepath):
    with open(filepath, 'wb') as file:

        ctx = {
            'context': context,
            'delayed': {},
            'bnames': [],
            'matnames': [],
            'objnames': [],
            'obj': [],
            'polytagcount': 0,
            'bonecount': 0,
            'rigged': False
        }
        
        for o in context.scene.objects:
            if o.type == 'MESH':
                ctx['objnames'].append(cut_name(o.name))
                ctx['obj'].append(o)
                # name = cut(o.name)
                #  if (name not in ctx['objnames'][:]):
                #      ctx['objnames'].append([])
            if o.type == 'ARMATURE':
                 ctx['bonecount'] = len(o.data.bones)
                 #from . import VBNRead
                 #ctx['bnames'] = VBNRead.readVBN()
                 for bone in o.data.bones:
                     ctx['bnames'].append(bone.name)
                 print(ctx['bnames'])
                 ctx['rigged'] = True
        
        #Write the header
        file.write(b'NDP3')
        write_delayed(ctx, file, 'filesize', '>l', (0,))
        write_struct_to_file(file, '>HHHH', (0x200, len(ctx['objnames']), 0x2, ctx['bonecount']))

        write_delayed(ctx, file, 'trioffset', '>l', (0,))
        write_delayed(ctx, file, 'trisize', '>l', (0,))
        write_delayed(ctx, file, 'uvsize', '>l', (0,))
        write_delayed(ctx, file, 'vertsize', '>l', (0,))
        
        #Write first float gunk
        write_struct_to_file(file, '>IIII', (0xBE99BDA8,0x40F4EA5C,0x406E388D,0x411884B7))

        #Write object tags
        write_n_items(ctx, file, len(ctx['objnames']), write_obj_tag)
        
        #Write poly tags
        write_n_items(ctx, file, ctx['polytagcount'], write_poly_tag)
        
        #Write materials
        write_n_items(ctx, file, ctx['polytagcount'], write_materials)
        
        if(file.tell() % 16):
            write_n_items(ctx, file, 16 - (file.tell() % 16), add_padding)
        
        ctx['trioffset'] = file.tell()
        resolve_delayed(ctx, file, 'trioffset', (file.tell() - 0x30,))

        #Write tris
        write_n_items(ctx, file, ctx['polytagcount'], write_tris)
        
        if(file.tell() % 16):
            write_n_items(ctx, file, 16 - (file.tell() % 16), add_padding)
        
        resolve_delayed(ctx, file, 'trisize', (file.tell() - ctx['trioffset'],))
        
        if (ctx['rigged'] == True):
            ctx['uvoffset'] = file.tell()
            
            #Write uvcol data
            write_n_items(ctx, file, ctx['polytagcount'], write_uvcols)
        
            ctx['vertoffset'] = file.tell()
            resolve_delayed(ctx, file, 'uvsize', (ctx['vertoffset'] - ctx['uvoffset'],))
        
            #Write vert data
            write_n_items(ctx, file, ctx['polytagcount'], write_verts)
        
            if((file.tell()) % 16):
                write_n_items(ctx, file, 16 - (file.tell() % 16), add_padding)
        
            resolve_delayed(ctx, file, 'vertsize', (file.tell() - ctx['vertoffset'],))

        else:
            #Write vert data
            ctx['vertoffset'] = file.tell()

            resolve_delayed(ctx, file, 'vertsize', (0x0,))
            
            write_n_items(ctx, file, ctx['polytagcount'], write_static_verts)
            
            if((file.tell()) % 16):
                write_n_items(ctx, file, 16 - (file.tell() % 16), add_padding)
            
            resolve_delayed(ctx, file, 'uvsize', (file.tell() - ctx['vertoffset'],))

            
        ctx['nameoffset'] = file.tell()
        write_n_items(ctx, file, len(ctx['objnames']), write_names)
        
        resolve_delayed(ctx, file, 'filesize', (file.tell(),))

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper

class ExportNUD(bpy.types.Operator, ExportHelper):
    '''Export a Smash 4 NUD file'''
    bl_idname = "model.nud"
    bl_label = 'Export NUD'
    filename_ext = ".nud"
    filter_glob = StringProperty(default="*.nud", options={'HIDDEN'})
    
    def execute(self, context):
        writeNUD(context, self.filepath)
        return {'FINISHED'}

def menu_func_export(self, context):
    self.layout.operator(ExportNUD.bl_idname, text="Super Smash Bros. for Wii U Model (.nud)")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)
    
if __name__ == "__main__":
    register()