bl_info = {
    "name": "Smash 4 Model (.nud)",
    "author": "mvit",
    "version": (0,0,1),
    "blender": (2,6,9),
    "location": "File > Import > Smash 4 Model",
    "warning": "EXPERIMENTAL RELEASE",
    "category": "Import"
}

import bpy
import struct

def read_n_items(ctx, file, n, offset, func):
    file.seek(offset)
    for i in range(n):
        func(ctx, i, file)

def cleanup_string(b):
    return b.replace(b'\0', b'').decode('utf-8', errors='ignore')

#Half to Float provided by http://fpmurphy.blogspot.com/
def half_to_float(h):
    s = int((h >> 15) & 0x00000001)     # sign
    e = int((h >> 10) & 0x0000001f)     # exponent
    f = int(h &         0x000003ff)     # fraction

    if e == 0:
       if f == 0:
          return int(s << 31)
       else:
          while not (f & 0x00000400):
             f <<= 1
             e -= 1
          e += 1
          f &= ~0x00000400
    elif e == 31:
       if f == 0:
          return int((s << 31) | 0x7f800000)
       else:
          return int((s << 31) | 0x7f800000 | (f << 13))

    e = e + (127 -15)
    f = f << 13

    return int((s << 31) | (e << 23) | f)

def decompress(h):
    float16 = half_to_float(h)
    str = struct.pack('I',float16)
    f=struct.unpack('f', str)
    return f[0]

def read_struct_from_file(file, fmt):
    return struct.unpack(fmt, file.read(struct.calcsize(fmt)))

def read_names(ctx, i, file):
    name = read_struct_from_file(file, '<32s')[0]
    name = cleanup_string(name)
    ctx['objnames'].append(name)

def make_UV_map(ctx):
    for poly in ctx['mesh'].polygons:
        for i in range(poly.loop_start, poly.loop_start + poly.loop_total):
            vidx = ctx['mesh'].loops[i].vertex_index
            ctx['uvdata'][i].uv = ctx['uv'][vidx]

def make_color_layer(ctx):
    for poly in ctx['mesh'].polygons:
        for i in range(poly.loop_start, poly.loop_start + poly.loop_total):
            vidx = ctx['mesh'].loops[i].vertex_index
            ctx['cdata'][i].color = ctx['col'][vidx]            

def read_surface_vert(ctx, i, file):
    x, y, z = read_struct_from_file(file, '>fff')
    ctx['verts'][i].co = (x,-1*z,y)

def read_surface_normal(ctx, i, file):
    x, y, z, n = read_struct_from_file(file, '>HHHH')
    fx = decompress(x)
    fy = decompress(y)
    fz = decompress(z)
    ctx['verts'][i].normal = (fx,-1*fz,-1*fy)

def read_surface_bone_normal(ctx, i, file):
    x, y, z, n = read_struct_from_file(file, '>HHHH')
    bx = decompress(x)
    by = decompress(y)
    bz = decompress(z)
    bn = decompress(n)
    #print("bone somethings")
    #print({bx,by,bz,bn})
    #ctx['verts'][i].normal = (fx,fz,fy)

def read_surface_tan_normal(ctx, i, file):
    x, y, z, n = read_struct_from_file(file, '>HHHH')
    tanx = decompress(x)
    tany = decompress(y)
    tanz = decompress(z)
    tann = decompress(n)
    #print("tan somethings")
    #print({tanx, tany, tanz, tann})
    #ctx['verts'][i].normal = (fx,fz,fy)

def read_surface_uv_point(ctx, i, file):
    tag = ctx['cur_tag']
    count = tag['uvsize']//0x10
    #print("Found %d UV Maps" % count)
    
    for i in range(count):
        u, v = read_struct_from_file(file, '>HH')    
        fu = decompress(u) * 2
        fv = 1 - ((decompress(v) *2) - 1)
        ctx['uv'][i].append((fu,fv))
    
def read_surface_bone(ctx, i, file):
    b1, b2, b3, b4 = read_struct_from_file(file, '>BBBB')
    print("bones")
    print((b1+1,b2+1,b3+1,b4+1))
    #ctx['col'].append((r/255,g/255,b/255))

def read_surface_weight(ctx, i, file):
    w1, w2, w3, w4 = read_struct_from_file(file, '>BBBB')
    print("weights")
    print((w1/255,w2/255,w3/255,w4/255))
    #ctx['col'].append((r/255,g/255,b/255))

def read_surface_color(ctx, i, file):
    tag = ctx['cur_tag']

    if not (tag['uvsize'] == 0x10):
        r, g, b, a = read_struct_from_file(file, '>BBBB')
        ctx['col'].append((r/255,g/255,b/255))
    else:
        ctx['col'].append((255, 255, 255))

def read_surface_triangle(ctx, i, file):
    a, b, c = read_struct_from_file(file, '>HHH')
    ls = i*3;
    ctx['mesh'].loops[ls].vertex_index = a
    ctx['mesh'].loops[ls+1].vertex_index = b
    ctx['mesh'].loops[ls+2].vertex_index = c
    ctx['mesh'].polygons[i].loop_start = ls
    ctx['mesh'].polygons[i].loop_total = 3
    ctx['mesh'].polygons[i].use_smooth = True

def read_surface_data(ctx, i, file):
    read_surface_color(ctx, i, file)
    read_surface_uv_point(ctx,i,file)

def read_surface_rigged_mesh(ctx, i, file):
    tag = ctx['cur_tag']
    read_surface_vert(ctx,i,file)
    read_surface_normal(ctx,i,file)
    
    if(tag['vsize'] == 0x47):
        read_surface_bone_normal(ctx, i, file)
        read_surface_tan_normal(ctx, i, file)
    
    read_surface_bone(ctx, i, file)
    read_surface_weight(ctx, i, file)

def read_surface_static(ctx, i, file):
    read_surface_vert(ctx, i, file)
    file.seek(0x4, 1)
    read_surface_color(ctx, i, file)
    read_surface_uv_point(ctx, i, file)

def read_surface_static_mesh(ctx, i, file):
    read_surface_vert(ctx,i,file)
    read_surface_normal(ctx,i,file)
    read_surface_color(ctx, i, file)
    read_surface_uv_point(ctx, i, file)

def read_surface_VIS_mesh(ctx, i, file):
    read_surface_vert(ctx,i,file)
    read_surface_normal(ctx,i,file)
    read_surface_bone_normal(ctx, i, file)
    read_surface_tan_normal(ctx, i, file)
    read_surface_color(ctx, i, file)
    read_surface_uv_point(ctx, i, file)
    
def read_obj_tag(ctx, i, file):
  #Skip checksum (?) sector
  file.seek(0x20, 1) 
  print(hex(file.tell()))
  
  namepnt, idA, bind, count, objsect\
  = read_struct_from_file(file, '>llHHl')
  
  tag = {
    'index': i,
    'idA': idA,
    'bind': bind,
    'nameoff': namepnt, 
    'count': count, 
    'objoff': objsect,
    'polytags': [],
  }
  
  print("obj %d has bind %x and idA %x" % (i, bind, idA))
  ctx['obj_cnt'] += 1
  ctx['obj_tag'].append(tag)

def read_poly_tags(ctx, i, file):

  polytag = ctx['obj_tag'][i]  
  read_n_items(polytag, file, polytag['count'], polytag['objoff'], read_poly_tag)

def read_poly_tag(ctx, i, file):
  
  pstart, vstart, vastart, vcount, vsize, uvsize,\
  tx1, tx2, tx3, tx4, pcount, psize, pflag, padding\
  = read_struct_from_file(file, '>lllHBBllllHbb12s')
  
  tag = {
    'pflag': pflag,
    'pstart':pstart,
    'vstart':vstart,
    'vastart':vastart,
    'vcount': vcount,
    'pcount': pcount,
    'vsize' : vsize,
    'uvsize' : uvsize,
    'psize': psize,
    'index': i,
  }
  ctx['polytags'].append(tag)

def read_surface(ctx, i ,file):
    
    objtag = ctx['obj_tag'][i]
    
    print("Obj Tag:" + str(objtag['index']))    
    print("Bind is %d", objtag["bind"])
    nameoffset = ctx['nameoffset'] + objtag['nameoff']
    print(hex(nameoffset))
    read_n_items(ctx, file, 1, nameoffset, read_names)
    print(ctx['objnames'][i])

    polytags = objtag['polytags'] 
    print("Polytag amount: %d" % (len(polytags)))
    for tag in polytags:
      print("Poly Tag:" + str(tag['index']))
      print("vsize %x, uvsize %x, psize" % (tag['vsize'], tag['uvsize']))
      print(tag['psize'])
      print("pflag")
      print(tag['pflag'])
      
      ctx['cur_tag'] = tag;
      
      pcount = tag['pcount']//3
      vcount = tag['vcount']
      
      print("vcount: %d, pcount: %d" % (pcount, vcount))
      
      pstart = tag['pstart'] + ctx['polyoffset']
      vstart = tag['vstart'] + ctx['vertoffset']
      vastart = tag['vastart'] + ctx['vrtaoffset']
      
      print("vstart: %x, vastart: %x" % (pstart, vastart))

      ctx['mesh'] = bpy.data.meshes.new(ctx['objnames'][i])
      ctx['mesh'].vertices.add(count=vcount)
      ctx['mesh'].polygons.add(count=pcount)
      ctx['mesh'].loops.add(count=pcount*3)

      ctx['verts'] = ctx['mesh'].vertices
      ctx['uv'] = ([],[],[],[])
      ctx['col'] = []

      #read tris
      read_n_items(ctx, file, pcount, pstart, read_surface_triangle)
      #read verts
      if (tag['vsize'] == 0x00):
          #if(tag['uvsize'] <= 0x12):
          read_n_items(ctx, file, vcount, vstart, read_surface_static)
      elif (tag['vsize'] == 0x06):
          read_n_items(ctx, file, vcount, vstart, read_surface_static_mesh)
      elif (tag['vsize'] == 0x07):
          print("VIS model")
          read_n_items(ctx, file, vcount, vstart, read_surface_VIS_mesh)
      else:
          print("Rigged model")
          read_n_items(ctx, file, vcount, vstart, read_surface_data)
          read_n_items(ctx, file, vcount, vastart, read_surface_rigged_mesh)
      
      #reconstruct UV and Color layer

      #ctx['mesh'].uv_textures.new('UVMap')
      #ctx['uvdata'] = ctx['mesh'].uv_layers['UVMap'].data
      #ctx['mesh'].vertex_colors.new('Col')
      #ctx['cdata'] = ctx['mesh'].vertex_colors['Col'].data
      
      #make_UV_map(ctx)
      #make_color_layer(ctx)
      
      #Refresh Mesh
      ctx['mesh'].update(calc_edges=True)
      
      #Read object name
      obj = bpy.data.objects.new(ctx['objnames'][i], ctx['mesh'])
      ctx['context'].scene.objects.link(obj)

def read_NUD(context, filepath):
    with open(filepath, 'rb') as file:
        print("Starting Import")
        
        magic, fsize, ver, objcount, nid, bonecount, objpnt, objsize,\
        vtxsize, vtasize\
        = read_struct_from_file(file, '>4slHHHHllll')
        
        polyoffset = objpnt + 0x30
        vertoffset = polyoffset + objsize
        vrtaoffset = vertoffset + vtxsize
        nameoffset = vrtaoffset + vtasize
        print(hex(vtasize))
                
        ctx = {
        'context': context,
        'objnames': [],
        'obj_tag': [],
        'obj_cnt': 0,
        'vtasize': vtasize,
        'polyoffset': polyoffset,
        'vertoffset': vertoffset,
        'vrtaoffset': vrtaoffset,
        'nameoffset': nameoffset,
        }
        print('polysize %x, vertsize %x, vrtasize %x' % (objsize, vtxsize, vtasize))
        file.seek(0x10,1)
        
        #Get Obj Tags
        read_n_items(ctx, file, objcount, file.tell(), read_obj_tag)
        
        #Get Poly Tags
        read_n_items(ctx, file, ctx['obj_cnt'], file.tell(), read_poly_tags)
        
        #Get Shaders
        #read_n_items(ctx, file, , file.tell(), read_shaders)
        
        #Read the Surface
        read_n_items(ctx, file, ctx['obj_cnt'], ctx['polyoffset'], read_surface)
         
    return {'FINISHED'}

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator

class ImportNUD(Operator, ImportHelper):
    '''Import a Smash 4 NUD file'''
    bl_idname = "model.nud"
    bl_label = 'Import NUD'
    filename_ext = ".nud"
    filter_glob = StringProperty(default="*.nud", options={'HIDDEN'})

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

    def execute(self, context):
        return read_NUD(context, self.filepath)

def menu_func_import(self, context):
    self.layout.operator(ImportNUD.bl_idname, text="Super Smash Bros. 4 Model (.NUD)")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
