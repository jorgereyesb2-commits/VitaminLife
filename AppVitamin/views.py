from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import MetodoEnvio, Venta, DetalleVenta, Producto, Usuario, Perfil
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password 
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from django.db.models import Max
from django.utils.timezone import now
from .models import *
from django.db import transaction  
from datetime import datetime
from django.db.models import F



def listar_envios(request):
    # Obtener el usuario autenticado
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(pk=usuario_id) if usuario_id else None

    # Obtener los métodos de envío
    envios = MetodoEnvio.objects.all()

    return render(request, 'envios/listar_envios.html', {
        'envios': envios,
        'usuario': usuario,  # Pasar el usuario autenticado
    })


def crear_envio(request):
    # Obtener el usuario autenticado para la navbar
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(pk=usuario_id) if usuario_id else None

    if request.method == 'POST':
        # Capturar el nombre del método de envío
        nombre_envio = request.POST['nombre']  # Captura el nombre del método de envío

        # Crear el método de envío y almacenar el objeto creado
        metodo_envio = MetodoEnvio.objects.create(
            nombre=nombre_envio,
            costo=request.POST['costo'],
            tiempo_estimado=request.POST['tiempo_estimado'],
        )

        # Mensaje de éxito
        messages.success(request, 'El método de envío se creó correctamente.')

        # Registrar acción con el nombre capturado y el ID del registro creado
        registrar_accion(usuario, 'Crear', 'MetodoEnvio', metodo_envio.envio_id, f'Ha creado el método de envío "{nombre_envio}".')
        
        # Permanecer en la misma página
        return render(request, 'envios/crear_envio.html', {
            'usuario': usuario
        })

    return render(request, 'envios/crear_envio.html', {
        'usuario': usuario
    })



# Vista para editar un envio existente
def editar_envio(request, envio_id):
    envio = get_object_or_404(MetodoEnvio, envio_id=envio_id)

    # Obtener el usuario autenticado para mostrar en la navbar
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(pk=usuario_id) if usuario_id else None

    if request.method == 'POST':
        envio.nombre = request.POST['nombre']
        envio.costo = request.POST['costo']
        envio.tiempo_estimado = request.POST['tiempo_estimado']
        envio.save()
        messages.success(request, 'Los cambios se realizaron con éxito.')

        # Registrar la acción de edición
        registrar_accion(usuario, 'Editar Envios', 'MetodoEnvio', envio_id, f'Ha editado el método de envío "{envio.nombre}".')

    return render(request, 'envios/editar_envio.html', {
        'envio': envio,
        'usuario': usuario,
    })




# Vista para eliminar un envío
def eliminar_envio(request, envio_id):
    envios = get_object_or_404(MetodoEnvio, envio_id=envio_id)

    # Obtener el usuario autenticado para mostrar en la navbar
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(pk=usuario_id) if usuario_id else None

    if request.method == 'POST':
        # Registrar la acción antes de eliminar el envío
        registrar_accion(usuario, 'Eliminar', 'MetodoEnvio', envio_id, f'Ha eliminado el método de envío "{envios.nombre}".')
        
        envios.delete()
        messages.success(request, 'El método de envío se eliminó correctamente.')  # Mensaje de éxito
        return redirect('listar_envios')  # Redirigir a listar_envios

    return render(request, 'envios/eliminar_envio.html', {'envios': envios})



def toggle_estado_envio(request, envio_id):
    envios = get_object_or_404(MetodoEnvio, pk=envio_id)

    # Obtener el usuario autenticado para mostrar en la navbar
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(pk=usuario_id) if usuario_id else None

    # Cambiar el estado habilitado del envío
    envios.habilitado = not envios.habilitado

    # Registrar la acción de habilitar/deshabilitar
    estado = "habilitado" if envios.habilitado else "deshabilitado"
    registrar_accion(usuario, 'Cambiar Estado', 'MetodoEnvio', envio_id, f'El método de envío "{envios.nombre}" ha sido {estado}.')

    envios.save()
    return redirect('listar_envios')


#-----------------------------------------------------------------------

# FUNCIONES PARA HISTORIAL DE COMPRAS Y SEGUIMIENTO DE PEDIDOS (CLIENTE)

#-----------------------------------------------------------------------

def historial_compra(request):
    # Verificar si el usuario ha iniciado sesión mediante la sesión
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('iniciar_sesion')  # Redirigir si no está autenticado

    # Obtener el usuario autenticado
    usuario = Usuario.objects.get(pk=usuario_id)

    # Obtener las compras asociadas al usuario autenticado, ordenadas por fecha descendente
    compras = Venta.objects.filter(usuario=usuario).order_by('-fecha')


    # para que numero del carrito en el nav funcione
    total_productos = contar_productos_carrito(usuario_id)

    # Obtener productos comprados por el usuario (agrupando por producto para evitar duplicados)
    productos_comprados = DetalleVenta.objects.filter(venta__usuario=usuario).values(
        'producto__producto_id',
        'producto__nombre',
        'producto__precio'
    ).annotate(ultima_compra=Max('venta__fecha')).order_by('-ultima_compra')  # Ordenar por fecha descendente

    # Renderizar la página con los datos del usuario, las compras y los productos
    return render(request, 'compras/historial_compra.html', {
        'usuario': usuario,  # Para mostrar datos del usuario en la navbar
        'ventas': compras,   # Compras ordenadas por fecha descendente
        'productos_comprados': productos_comprados,  # Productos comprados en el pasado
        # para que numero del carrito en el nav funcione
        'total_productos': total_productos,
    
    })


def seguimiento_pedidos(request):
    # Verificar si el usuario ha iniciado sesión
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para ver el seguimiento de tus pedidos.")
        return redirect('iniciar_sesion')

    # Obtener el usuario autenticado
    usuario = Usuario.objects.get(pk=usuario_id)

    # Obtener los pedidos (ventas) asociados al usuario
    pedidos = Venta.objects.filter(usuario=usuario)

    # Renderizar la página con los pedidos y el usuario en el contexto
    return render(request, 'compras/seguimiento_pedidos.html', {
        'pedidos': pedidos,
        'usuario': usuario,
    })



### PAra actualizar perfil cliente
def actualizar_perfil_cliente(request):
    # Obtener el usuario autenticado desde la sesión
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(pk=usuario_id) if usuario_id else None

    if not usuario:
        # Redirigir a inicio de sesión si no hay usuario autenticado
        return redirect('iniciar_sesion')

    if request.method == 'POST':
        usuario.nombre = request.POST.get('nombre', usuario.nombre)
        usuario.primer_apellido = request.POST.get('primer_apellido', usuario.primer_apellido)
        usuario.segundo_apellido = request.POST.get('segundo_apellido', usuario.segundo_apellido)
        usuario.correo = request.POST.get('correo', usuario.correo)
        usuario.telefono = request.POST.get('telefono', usuario.telefono)
        usuario.direccion_envio = request.POST.get('direccion_envio', usuario.direccion_envio)
        usuario.save()
        messages.success(request, '¡Perfil actualizado exitosamente!')

        registrar_accion(usuario, 'Actualizar', 'Usuario', usuario.usuario_id, f'El usuario "{usuario.nombre} {usuario.primer_apellido}" actualizó su perfil.')

        
        return redirect('perfil_cliente')

    return render(request, 'usuarios/EditarPerfilCliente.html', {'usuario': usuario})




### FUNCION DE PARA LISTAR VENTAS
def listar_ventas(request):
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(pk=usuario_id) if usuario_id else None

    # filtros
    venta_id = request.GET.get('venta_id')
    rut = request.GET.get('rut')
    apellido = request.GET.get('apellido')

    # Filtra las ventas
    ventas = Venta.objects.all()

    if venta_id:
        ventas = ventas.filter(venta_id=venta_id)
    if rut:
        ventas = ventas.filter(usuario__rut__icontains=rut)
    if apellido:
        ventas = ventas.filter(usuario__primer_apellido__icontains=apellido)

    return render(request, 'ventas/listar_ventas.html', {
        'ventas': ventas,
        'usuario': usuario,
    })




def detalle_venta(request, venta_id):
    # Obtener el usuario autenticado para la navbar
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(pk=usuario_id) if usuario_id else None

    # Obtener los detalles de la venta
    venta = get_object_or_404(Venta, pk=venta_id)
    detalles = DetalleVenta.objects.filter(venta=venta)  # Filtrar por la venta específica

    # Pasar el usuario y los detalles a la plantilla
    return render(request, 'ventas/detalle_venta.html', {
        'venta': venta,
        'detalles': detalles,
        'usuario': usuario,  # Pasar el usuario autenticado
    })



###--------------------------------------------------------------
###          PRODUCTOS
###--------------------------------------------------------------


def productos_inicio(request):
    productos = Producto.objects.filter(habilitado=True)
    return render(request, 'productos/productos_inicio.html', {'productos': productos})




def listar_productos(request):
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(pk=usuario_id) if usuario_id else None

    productos = Producto.objects.all()

    # Convertir precios a enteros para eliminar los decimales
    for producto in productos:
        producto.precio = int(producto.precio)

    return render(request, 'productos/listar_productos.html', {
        'productos': productos,
        'usuario': usuario,  # Pasar el usuario autenticado
    })


# Vista para crear un nuevo producto
def crear_producto(request):
    # Obtener el usuario autenticado para la navbar
    usuario_actual_id = request.session.get('usuario_id')
    usuario_actual = Usuario.objects.get(pk=usuario_actual_id) if usuario_actual_id else None

    if request.method == 'POST':
        # Procesar la imagen cargada
        imagen_producto = request.FILES.get('imagen_producto')
        imagen_url = f'images/{imagen_producto.name}' if imagen_producto else ''

        # Crear el producto
        producto = Producto.objects.create(
            sku=request.POST['sku'],
            nombre=request.POST['nombre'],
            descripcion=request.POST.get('descripcion', ''),
            categoria=request.POST.get('categoria', ''),
            informacion_nutricional=request.POST.get('informacion_nutricional', ''),
            dosificacion=request.POST.get('dosificacion', ''),
            contenido_envase=request.POST.get('contenido_envase', ''),
            precio=request.POST['precio'],
            imagen_url=imagen_url
        )

        registrar_accion(usuario_actual, 'Crear', 'Producto', producto.producto_id, f'Se ha creado el producto "{producto.nombre}".')

        # Mensaje de éxito
        messages.success(request, 'Producto creado exitosamente.')

        # Mantente en la misma página con los campos limpios
        return render(request, 'productos/crear_producto.html', {
            'usuario': usuario_actual
        })

    return render(request, 'productos/crear_producto.html', {
        'usuario': usuario_actual
    })



# Vista para editar un producto existente
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, producto_id=producto_id)
    
    # Obtener usuario para la navbar
    usuario_actual_id = request.session.get('usuario_id')
    usuario_actual = Usuario.objects.get(pk=usuario_actual_id) if usuario_actual_id else None

    if request.method == 'POST':
        producto.sku = request.POST['sku']
        producto.nombre = request.POST['nombre']
        producto.descripcion = request.POST.get('descripcion', '')
        producto.categoria = request.POST.get('categoria', '')
        producto.informacion_nutricional = request.POST.get('informacion_nutricional', '')
        producto.dosificacion = request.POST.get('dosificacion', '')
        producto.contenido_envase = request.POST.get('contenido_envase', '')
        producto.precio = request.POST['precio']

        # Procesar la imagen cargada
        imagen_producto = request.FILES.get('imagen_producto')
        if imagen_producto:
            # Guardar la imagen en la carpeta static/images
            imagen_nombre = f"images/{imagen_producto.name}"
            with open(f'static/{imagen_nombre}', 'wb+') as destination:
                for chunk in imagen_producto.chunks():
                    destination.write(chunk)
            producto.imagen_url = imagen_nombre

        producto.save()

        # Agregar mensaje de éxito
        messages.success(request, 'El producto ha sido actualizado exitosamente.')

         # **AÑADIR AQUÍ**: Registrar la acción
        registrar_accion(usuario_actual, 'Editar', 'Producto', producto.producto_id, f'Se ha editado el producto "{producto.nombre}".')

        

    return render(request, 'productos/editar_producto.html', {
        'producto': producto,
        'usuario': usuario_actual
    })




# Vista para eliminar un producto
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, producto_id=producto_id)
    if request.method == 'POST':
        producto.delete()
        return redirect('listar_productos')  # Redirigir a listar_productos

    return render(request, 'productos/eliminar_producto.html', {'producto': producto})


# cambiar estado del producto
def toggle_estado_producto(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    producto.habilitado = not producto.habilitado  # Cambiar el estado
    producto.save()  # Guardar cambios

    # **Obtener el usuario actual de la sesión**
    usuario_actual_id = request.session.get('usuario_id')
    usuario_actual = Usuario.objects.get(pk=usuario_actual_id) if usuario_actual_id else None

    # **Registrar la acción**
    if usuario_actual:
        registrar_accion(usuario_actual, 'Cambiar Estado', 'Producto', producto.producto_id, f'Se ha cambiado el estado del producto "{producto.nombre}".')

    return redirect('listar_productos')  # Redirigir a la lista de productos



def ficha_producto(request, producto_id):
    producto = get_object_or_404(Producto, producto_id=producto_id)
    return render(request, 'productos/ficha_producto.html', {'producto': producto})


##################################

# Para validar RUT
def validar_rut(rut, usuario_id=None):
    partes = rut.split('-')
    if len(partes) != 2:
        return False

    numeros = partes[0]
    digito_verificador = partes[1]

    if not numeros.isdigit():
        return False

    if len(numeros) < 7 or len(numeros) > 8:
        return False

    if not digito_verificador.isdigit() and digito_verificador.upper() != 'K':
        return False

    if len(digito_verificador) != 1:
        return False

    return True

# Para validar datos de usuario
def validar_datos_usuario(nombre, primer_apellido, segundo_apellido, rut, password, repassword, errores, usuario_id=None):
    if not nombre.isalpha():
        errores.append('El nombre solo debe contener letras y sin espacios.')
    elif len(nombre) > 20:
        errores.append(f'El nombre no debe superar los 20 caracteres. Tiene {len(nombre)} caracteres.')

    if not primer_apellido.isalpha():
        errores.append('El primer apellido solo debe contener letras.')
    elif len(primer_apellido) > 20:
        errores.append(f'El primer apellido no debe superar los 20 caracteres. Tiene {len(primer_apellido)} caracteres.')

    if not segundo_apellido.isalpha():
        errores.append('El segundo apellido solo debe contener letras.')
    elif len(segundo_apellido) > 20:
        errores.append(f'El segundo apellido no debe superar los 20 caracteres. Tiene {len(segundo_apellido)} caracteres.')

    if not validar_rut(rut, usuario_id):
        errores.append('El RUT ya está registrado o no tiene el formato correcto, ejemplo: 12345678-9.')

    if password and password != repassword:
        errores.append('Las contraseñas no coinciden.')

    return errores



# Para registrar usuario
def registrar_usuario(request):
    errores = []
    mensaje_exito = None

    if request.method == 'POST':
        nombre = request.POST['nombre']
        primer_apellido = request.POST['primer_apellido']
        segundo_apellido = request.POST['segundo_apellido']
        correo = request.POST['correo']
        rut = request.POST['rut']
        telefono = request.POST['telefono']
        direccion = request.POST['direccion']
        password = request.POST['password']
        repassword = request.POST['repassword']

        errores = validar_datos_usuario(nombre, primer_apellido, segundo_apellido, rut, password, repassword, errores)

        if not errores:
            try:
                perfil = Perfil.objects.get(perfil_id=2)  # Perfil 2 es Cliente
            except Perfil.DoesNotExist:
                errores.append('El perfil no existe.')
            else:
                try:
                    usuario = Usuario(
                        nombre=nombre.upper(),
                        primer_apellido=primer_apellido.upper(),
                        segundo_apellido=segundo_apellido.upper(),
                        correo=correo,
                        rut=rut,
                        telefono=telefono,
                        direccion_envio=direccion.upper(),
                        contrasena=password,
                        perfil=perfil
                    )

                    usuario.full_clean()
                    usuario.save()
                    
                    registrar_accion(usuario, 'Crear', 'Usuario', usuario.usuario_id, f'Se ha registrado al usuario "{usuario.nombre} {usuario.primer_apellido}".')


                    mensaje_exito = 'Usuario registrado exitosamente.'
                    # Dejar en blanco los campos después de un registro exitoso
                    nombre = ''
                    primer_apellido = ''
                    segundo_apellido = ''
                    correo = ''
                    rut = ''
                    telefono = ''
                    direccion = ''
                except ValidationError as e:
                    errores.extend(e.messages)

    return render(request, 'usuarios/RegistrarUsuario.html', {
        'errores': errores,
        'mensaje_exito': mensaje_exito,
        'nombre': nombre if 'nombre' in locals() else '',
        'primer_apellido': primer_apellido if 'primer_apellido' in locals() else '',
        'segundo_apellido': segundo_apellido if 'segundo_apellido' in locals() else '',
        'correo': correo if 'correo' in locals() else '',
        'rut': rut if 'rut' in locals() else '',
        'telefono': telefono if 'telefono' in locals() else '',
        'direccion': direccion if 'direccion' in locals() else '',
        'perfil': 'Cliente'  # Perfil por defecto
    })




# Para iniciar sesión
def iniciar_sesion(request):
    errores = []

    if request.method == 'POST':
        rut = request.POST['rut']
        password = request.POST['password']

        # Validar formato del RUT
        if not validar_rut(rut):
            errores.append('El RUT no tiene el formato correcto, ejemplo: 12345678-9.')
        else:
            try:
                # Buscar usuario por RUT
                usuario = Usuario.objects.get(rut=rut)

                # Verificar si la cuenta está suspendida
                if usuario.cuenta_suspendida:
                    errores.append('La cuenta está deshabilitada. Contacte al administrador.')
                    registrar_accion(usuario, 'Iniciar', 'Usuario', usuario.usuario_id, 'Cuenta bloqueada intento loguearse.')
                else:
                    # Verificar contraseña
                    if usuario.contrasena == password:
                        # Restablecer intentos fallidos
                        usuario.intentos_inicio_sesion = 0
                        usuario.save()

                        # Guardar el ID del usuario en la sesión
                        request.session['usuario_id'] = usuario.usuario_id


                        # Registrar accion
                        registrar_accion(usuario, 'Iniciar', 'Usuario', usuario.usuario_id, 'Inicio de sesión exitoso.')

                        
                        # Redirigir según el perfil
                        if usuario.perfil:
                            perfil_nombre = usuario.perfil.nombre.upper()
                            if perfil_nombre == 'ADMINISTRADOR':
                                return redirect('perfil_administrador')
                            elif perfil_nombre == 'CLIENTE':
                                return redirect('perfil_cliente')
                            else:
                                errores.append('Perfil de usuario desconocido.')
                        else:
                            errores.append('El usuario no tiene un perfil asignado.')
                    else:
                        # Incrementar intentos fallidos
                        usuario.intentos_inicio_sesion = F('intentos_inicio_sesion') + 1
                        usuario.save()

                        # Refrescar el objeto usuario
                        usuario.refresh_from_db()

                        # Suspender cuenta si llega al límite
                        if usuario.intentos_inicio_sesion >= 3:
                            usuario.cuenta_suspendida = True
                            usuario.save()
                            errores.append('La cuenta ha sido suspendida tras múltiples intentos fallidos. Contacte al administrador.')
                            registrar_accion(usuario, 'Iniciar', 'Usuario', usuario.usuario_id, 'Cuenta bloqueada por intentos de contraseña fallidos.')
                        else:
                            errores.append(f'RUT o contraseña incorrectos. Intentos restantes: {3 - usuario.intentos_inicio_sesion}')
            except Usuario.DoesNotExist:
                errores.append('RUT o contraseña incorrectos.')

    return render(request, 'usuarios/IniciarSesion.html', {'errores': errores})


# Para editar usuario
def editar_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, pk=usuario_id)
    errores = []
    mensaje_exito = None

    if request.method == 'POST':
        usuario.nombre = request.POST['nombre']
        usuario.primer_apellido = request.POST['primer_apellido']
        usuario.segundo_apellido = request.POST['segundo_apellido']
        usuario.correo = request.POST['correo']
        usuario.rut = request.POST['rut']
        usuario.telefono = request.POST['telefono']
        usuario.direccion_envio = request.POST['direccion']
        password = request.POST.get('password', '')
        repassword = request.POST.get('repassword', '')

        # Solo validar la contraseña si se ingresa una nueva
        if password or repassword:
            errores = validar_datos_usuario(usuario.nombre, usuario.primer_apellido, usuario.segundo_apellido, usuario.rut, password, repassword, errores, usuario_id)
            if not errores:
                usuario.contrasena = password  # Cambiar la contraseña solo si hay una nueva
        else:
            errores = validar_datos_usuario(usuario.nombre, usuario.primer_apellido, usuario.segundo_apellido, usuario.rut, None, None, errores, usuario_id)

        if not errores:
            try:
                usuario.full_clean()
                usuario.save()
                mensaje_exito = 'Usuario actualizado exitosamente.'

                registrar_accion(request.session.get('usuario_id'), 'Editar', 'Usuario', usuario.id, f'Se editó al usuario "{usuario.nombre} {usuario.primer_apellido}".')


            except ValidationError as e:
                errores.extend(e.messages)

    return render(request, 'usuarios/RegistrarUsuario.html', {
        'errores': errores,
        'mensaje_exito': mensaje_exito,
        'nombre': usuario.nombre,
        'primer_apellido': usuario.primer_apellido,
        'segundo_apellido': usuario.segundo_apellido,
        'correo': usuario.correo,
        'rut': usuario.rut,
        'telefono': usuario.telefono,
        'direccion': usuario.direccion_envio,
        'perfil': usuario.perfil.nombre,  # Muestra el nombre del perfil (Administrador o Cliente)
        'usuario_id': usuario_id  # Para distinguir que estamos en modo edición
    })

# Actualizar Perfil

# @login_required
def actualizar_perfil(request):
    usuario_id = request.session.get('usuario_id')  # Obtener el ID del usuario desde la sesión
    if not usuario_id:
        return redirect('iniciar_sesion')  # Redirigir si no está autenticado

    # Obtener el usuario desde la base de datos
    usuario = Usuario.objects.get(pk=usuario_id)
    if request.method == 'POST':
        # Recuperar datos del formulario
        usuario.nombre = request.POST.get('nombre')
        usuario.primer_apellido = request.POST.get('primer_apellido')
        usuario.segundo_apellido = request.POST.get('segundo_apellido', '')
        usuario.correo = request.POST.get('correo')
        usuario.telefono = request.POST.get('telefono')
        nueva_contrasena = request.POST.get('contrasena')

        # Si hay nueva contraseña, encriptarla antes de guardarla
        if nueva_contrasena:
            usuario.contrasena = make_password(nueva_contrasena)
        
        usuario.direccion_envio = request.POST.get('direccion_envio')

        # Guardar cambios en la base de datos
        usuario.save()
        
        # Redirigir al perfil después de la actualización
        return redirect('perfil_administrador')
    
    return render(request, 'usuarios/EditarPerfilAdministrador.html', {'usuario': usuario})


# Deshabilitar/habilitar usuario
def toggle_estado_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, pk=usuario_id)
    usuario.cuenta_suspendida = not usuario.cuenta_suspendida

    if not usuario.cuenta_suspendida:
        usuario.intentos_inicio_sesion = 0

    usuario.save()

    # *** Registrar la acción ***
    usuario_responsable = Usuario.objects.get(pk=request.session.get('usuario_id'))  # Obtener instancia del usuario responsable
    registrar_accion(usuario_responsable, 'Editar', 'Usuario', usuario.usuario_id, f'{"Habilitó" if not usuario.cuenta_suspendida else "Deshabilitó"} al usuario "{usuario.nombre} {usuario.primer_apellido}".')

    return redirect('gestion_usuarios')



# Cambiar el perfil de un usuario entre "Administrador" y "Cliente"
def toggle_perfil_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, pk=usuario_id)
    
    # Buscar el perfil de Administrador y Cliente
    perfil_admin = Perfil.objects.get(nombre='Administrador')
    perfil_cliente = Perfil.objects.get(nombre='Cliente')

    # Alternar entre los perfiles
    if usuario.perfil == perfil_admin:
        usuario.perfil = perfil_cliente
    else:
        usuario.perfil = perfil_admin


    # *** Registrar la acción ***
    usuario_responsable = Usuario.objects.get(pk=request.session.get('usuario_id'))  # Obtener instancia del usuario responsable
    registrar_accion(usuario_responsable, 'Cambiar perfil', 'Usuario', usuario.usuario_id, f'Cambió el perfil del usuario "{usuario.nombre} {usuario.primer_apellido}" a "{usuario.perfil.nombre}".')


    usuario.save()
    return redirect('gestion_usuarios')  # Usa el nombre de la vista



# Gestión de usuarios - muestra los datos
def gestion_usuarios(request):
    usuario_id = request.session.get('usuario_id')  # Obtener el usuario autenticado desde la sesión
    if not usuario_id:
        return redirect('iniciar_sesion')  # Redirigir si no está autenticado

    # Obtener el usuario autenticado
    usuario_actual = Usuario.objects.get(pk=usuario_id)

    # Obtener la lista de usuarios para la tabla
    usuarios = Usuario.objects.all()

    return render(request, 'usuarios/GestionUsuarios.html', {
        'usuarios': usuarios,
        'usuario': usuario_actual,  # Pasar el usuario autenticado al contexto
    })



# Para el perfil del cliente
def perfil_cliente(request):
    # Obtener el ID del usuario autenticado desde la sesión
    usuario_id = request.session.get('usuario_id')



    if not usuario_id:
        return redirect('usuarios/iniciar_sesion')  # Redirigir a la página de inicio de sesión si no está autenticado

    # Obtener los datos del usuario autenticado
    usuario = Usuario.objects.get(pk=usuario_id)

    # Mostrar la contraseña con asteriscos
    contrasena_oculta = '*' * len(usuario.contrasena)

    return render(request, 'usuarios/PerfilCliente.html', {
        'usuario': usuario,
        'contrasena_oculta': contrasena_oculta  # Para mostrar la contraseña con *
    })




def perfil_administrador(request):
    # Obtener el ID del usuario autenticado desde la sesión
    usuario_id = request.session.get('usuario_id')

    if not usuario_id:
        return redirect('iniciar_sesion')  # Redirigir a la página de inicio de sesión si no está autenticado

    # Obtener los datos del usuario autenticado
    usuario = Usuario.objects.get(pk=usuario_id)

    # No se oculta la contraseña en esta vista
    return render(request, 'usuarios/PerfilAdministrador.html', {
        'usuario': usuario,
        # No es necesario pasar contrasena_oculta
    })


#####-------------------------------------------------------------------------------
#####-------------------------------------------------------------------------------
#####-------------------------------------------------------------------------------
##### FUNCIONES REALIZADAS PARA EL CARRITO Y ALGUNAS COSAS DEL CLIENTE



def contar_productos_carrito(usuario_id):
    if not usuario_id:
        return 0
    carrito = Carrito.objects.filter(usuario_id=usuario_id).first()
    if carrito:
        return carrito.productos.count()
    return 0



def productos_cliente(request):
    productos = Producto.objects.filter(habilitado=True)  # Recupera todos los productos
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(pk=usuario_id) if usuario_id else None
    
    total_productos = contar_productos_carrito(usuario_id)  # Contar productos en el carrito

    context = {
        'productos': productos,
        'usuario': usuario,
        'total_productos': total_productos,
    }
    return render(request, 'productos/productos_cliente.html', context)


# Agrega esta función en otras vistas donde necesites el contador
def otra_vista(request):
    usuario_id = request.session.get('usuario_id')
    total_productos = contar_productos_carrito(usuario_id)  # Contar productos en el carrito

    context = {
        'total_productos': total_productos,
        # Otros contextos...
    }
    return render(request, 'otra_template.html', context)




def agregar_al_carrito(request, producto_id):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('iniciar_sesion')

    # Obtener o crear el carrito con el estado 'Activo'
    estado_carrito = EstadoCarrito.objects.get(nombre_estado='Activo')  # Instancia del estado
    carrito, created = Carrito.objects.get_or_create(usuario_id=usuario_id, estado=estado_carrito)

    # Obtener el producto
    producto = get_object_or_404(Producto, pk=producto_id)

    # Obtener la cantidad de la solicitud
    cantidad = int(request.GET.get('cantidad', 1))  # Por defecto, 1 si no se proporciona

    # Agregar o actualizar el producto en el carrito
    detalle, created = carrito.productos.get_or_create(
        producto=producto,
        defaults={'cantidad': cantidad, 'precio_unitario': producto.precio}
    )
    if not created:  # Si ya existe, incrementar la cantidad
        detalle.cantidad += cantidad  # Incrementar por la cantidad proporcionada
        detalle.save()

    return redirect('productos_cliente')





# Ver carrito
def ver_carrito(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('iniciar_sesion')

    # Obtener el usuario para la navbar
    usuario = Usuario.objects.get(pk=usuario_id)

    # Obtener o crear el carrito
    carrito, creado = Carrito.objects.get_or_create(usuario_id=usuario_id)

    # Asignar el estado "Activo"
    estado_activo = EstadoCarrito.objects.get(nombre_estado="Activo")
    carrito.estado = estado_activo
    carrito.save()

    productos_carrito = carrito.productos.all()
    total = sum(p.cantidad * p.precio_unitario for p in productos_carrito)

    # Contar los productos en el carrito
    total_productos = sum(item.cantidad for item in productos_carrito)

    # Calcular el total por producto
    for item in productos_carrito:
        item.total_producto = item.cantidad * item.precio_unitario

    return render(request, 'compras/carrito.html', {
        'usuario': usuario,  # Pasar el usuario al contexto
        'productos_carrito': productos_carrito,
        'total': total,
        'total_productos': total_productos,
    })


@csrf_exempt
def actualizar_cantidad(request, producto_id, cantidad):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return JsonResponse({'error': 'No estás autenticado'}, status=400)

    try:
        # Obtener el carrito activo del usuario
        carrito = Carrito.objects.get(usuario_id=usuario_id, estado__nombre_estado='Activo')
        producto_carrito = ProductoCarrito.objects.get(carrito=carrito, producto_id=producto_id)

        # Actualizar la cantidad del producto en el carrito
        producto_carrito.cantidad = cantidad
        producto_carrito.save()

        # Obtener el precio actualizado
        total_producto = producto_carrito.cantidad * producto_carrito.precio_unitario

        # Recargar el total del carrito
        total_carrito = sum(p.cantidad * p.precio_unitario for p in carrito.productos.all())

        # Devolver el total actualizado y el precio del producto
        return JsonResponse({
            'success': True,
            'total_producto': total_producto,
            'total_carrito': total_carrito,
            'cantidad': cantidad
        })

    except ProductoCarrito.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado en el carrito'}, status=400)


def eliminar_del_carrito(request, producto_id):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('iniciar_sesion')

    # Busca el estado "Activo"
    estado_activo = EstadoCarrito.objects.filter(nombre_estado='Activo').first()
    if not estado_activo:
        return redirect('ver_carrito')

    # Busca el carrito activo del usuario
    carrito = Carrito.objects.filter(usuario_id=usuario_id, estado=estado_activo).first()
    if carrito:
        # Busca el producto en el carrito y lo elimina
        producto_carrito = ProductoCarrito.objects.filter(carrito=carrito, producto_id=producto_id).first()
        if producto_carrito:
            producto_carrito.delete()

    return redirect('ver_carrito')







def resumen_carrito(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('iniciar_sesion')

    # Obtener el carrito activo del usuario
    carrito = get_object_or_404(Carrito, usuario_id=usuario_id, estado__nombre_estado="Activo")
    productos_carrito = carrito.productos.all()

    # Código para que funcione el número del nav del carrito
    total_productos = contar_productos_carrito(usuario_id)

    # Calcular el total del carrito
    total_carrito = sum(item.cantidad * item.precio_unitario for item in productos_carrito)

    # Calcular el total por producto y agregarlo al contexto
    for item in productos_carrito:
        item.total_producto = item.cantidad * item.precio_unitario  # Agregar el total del producto a cada item

    # Obtener métodos de pago y envío habilitados
    metodos_pago = MetodoPago.objects.filter(usuario_id=usuario_id, habilitado=True)
    metodos_envio = MetodoEnvio.objects.filter(habilitado=True)

    if request.method == 'POST':
        metodo_pago_id = request.POST.get('metodo_pago')
        metodo_envio_id = request.POST.get('metodo_envio')

        # Validar selecciones
        metodo_pago = get_object_or_404(MetodoPago, metodo_pago_id=metodo_pago_id, usuario_id=usuario_id, habilitado=True)
        metodo_envio = get_object_or_404(MetodoEnvio, envio_id=metodo_envio_id, habilitado=True)

        # Crear la venta
        estado_pedido = EstadoPedido.objects.get(nombre_estado="Pendiente")
        venta = Venta.objects.create(
            usuario_id=usuario_id,
            fecha=now(),
            total=total_carrito + metodo_envio.costo,
            estado=estado_pedido,
        )

        # Crear detalles de la venta
        for item in productos_carrito:
            DetalleVenta.objects.create(
                venta=venta,
                producto=item.producto,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
            )

        # Vaciar el carrito
        carrito.productos.all().delete()
        carrito.estado = EstadoCarrito.objects.get(nombre_estado="Pagado")
        carrito.save()

        return redirect('venta_exitosa', venta_id=venta.venta_id)

    return render(request, 'compras/resumen_carrito.html', {
        'productos_carrito': productos_carrito,
        'total_carrito': total_carrito,
        'metodos_pago': metodos_pago,
        'metodos_envio': metodos_envio,
        'total_productos': total_productos,
    })



### Ficha producto cliente
def ficha_producto_cliente(request, producto_id):
    # Obtener el producto de la base de datos
    producto = get_object_or_404(Producto, producto_id=producto_id)

    # Comprobar si el usuario está logueado a través del `usuario_id` en la sesión
    usuario = None
    if 'usuario_id' in request.session:
        # El usuario está logueado
        usuario_id = request.session['usuario_id']
        usuario = Usuario.objects.get(pk=usuario_id)
        
        # Recuperar el carrito del usuario
        carrito = Carrito.objects.filter(usuario_id=usuario_id).first()
        total_productos = carrito.productos.count() if carrito else 0

        return render(request, 'productos/ficha_producto_cliente.html', {
            'producto': producto,
            'usuario': usuario,  # Pasar el usuario autenticado
            'total_productos': total_productos,  # Agregamos el total de productos al contexto
        })
    else:
        # Si no está logueado, redirigir a la página de inicio de sesión
        return redirect('iniciar_sesion')





def darse_de_baja_cliente(request):
    if request.method == "POST":
        contrasena_ingresada = request.POST.get('contrasena')
        usuario_id = request.session.get('usuario_id')

        if not usuario_id:
            messages.error(request, "No estás autenticado. Por favor, inicia sesión.")
            return redirect('iniciar_sesion')

        try:
            usuario = Usuario.objects.get(pk=usuario_id)
            if usuario.contrasena == contrasena_ingresada:  # Comparación directa
                usuario.cuenta_suspendida = True
                usuario.save()

                registrar_accion(usuario, 'Deshabilitar', 'Usuario', usuario.usuario_id, f'El usuario "{usuario.nombre} {usuario.primer_apellido}" deshabilitó su cuenta.')

                request.session.flush()  # Cerrar sesión
                
                return redirect('productos_inicio')  # Redirigir después de deshabilitar
            else:
                messages.error(request, "La contraseña ingresada es incorrecta.")
                return redirect('actualizar_perfil_cliente')  # Volver al perfil si la contraseña es incorrecta
        except Usuario.DoesNotExist:
            messages.error(request, "El usuario no existe. Por favor, inicia sesión.")
            return redirect('iniciar_sesion')

    return redirect('perfil_cliente')



def perfil_cliente(request):
    usuario_id = request.session.get('usuario_id')  # Obtener el ID del usuario de la sesión
    usuario = Usuario.objects.get(pk=usuario_id) if usuario_id else None  # Obtener el usuario actual

    # Contar los productos en el carrito
    total_productos = contar_productos_carrito(usuario_id)

    return render(request, 'usuarios/PerfilCliente.html', {
        'usuario': usuario,
        'total_productos': total_productos,  # Agregar el total de productos al contexto
    })






#####-------------------------------------------------------------------------------
#####              AGREGADAS EN REVISION 01-12-24
#####-------------------------------------------------------------------------------


def editar_usuario_desde_admin(request, usuario_id):
    usuario = get_object_or_404(Usuario, pk=usuario_id)

    # Obtener el usuario autenticado para la navbar
    usuario_actual_id = request.session.get('usuario_id')
    usuario_actual = Usuario.objects.get(pk=usuario_actual_id) if usuario_actual_id else None

    if request.method == 'POST':
        usuario.nombre = request.POST.get('nombre')
        usuario.primer_apellido = request.POST.get('primer_apellido')
        usuario.segundo_apellido = request.POST.get('segundo_apellido', '')
        usuario.correo = request.POST.get('correo')
        usuario.telefono = request.POST.get('telefono')
        usuario.direccion_envio = request.POST.get('direccion_envio')
        usuario.save()
        # Mensaje de éxito
        messages.success(request, 'Los cambios se realizaron con éxito.')

        registrar_accion(usuario_actual, 'Editar', 'Usuario', usuario.usuario_id, f'El usuario "{usuario_actual.nombre} {usuario_actual.primer_apellido}" editó al usuario "{usuario.nombre} {usuario.primer_apellido}".')


        # Mantente en la misma página
        return render(request, 'usuarios/EditarUsuarioDesdeAdmin.html', {
            'usuario': usuario,
            'usuario_actual': usuario_actual,
        })

    return render(request, 'usuarios/EditarUsuarioDesdeAdmin.html', {
        'usuario': usuario,
        'usuario_actual': usuario_actual,
    })

def registrar_usuario_admin(request):
    # Obtener el usuario autenticado para la navbar
    usuario_actual_id = request.session.get('usuario_id')
    usuario_actual = Usuario.objects.get(pk=usuario_actual_id) if usuario_actual_id else None

    if request.method == 'POST':
        # Capturar datos del formulario
        nombre = request.POST.get('nombre', '').strip()
        primer_apellido = request.POST.get('primer_apellido', '').strip()
        segundo_apellido = request.POST.get('segundo_apellido', '').strip()
        correo = request.POST.get('correo', '').strip()
        rut = request.POST.get('rut', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        password = request.POST.get('password', '').strip()
        perfil_id = request.POST.get('perfil')

        # Validar si el RUT ya existe
        if Usuario.objects.filter(rut=rut).exists():
            messages.error(request, f'El RUT {rut} ya está registrado.')
        else:
            # Crear el nuevo usuario
            perfil = Perfil.objects.get(pk=perfil_id)
            nuevo_usuario = Usuario(
                nombre=nombre.upper(),
                primer_apellido=primer_apellido.upper(),
                segundo_apellido=segundo_apellido.upper(),
                correo=correo,
                rut=rut,
                telefono=telefono,
                direccion_envio=direccion.upper(),
                contrasena=password,  # Aquí puedes agregar encriptación si decides hacerlo luego
                perfil=perfil
            )
            nuevo_usuario.save()


            registrar_accion(usuario_actual, 'Registrar', 'Usuario', nuevo_usuario.usuario_id, f'El usuario "{usuario_actual.nombre} {usuario_actual.primer_apellido}" creó al usuario "{nuevo_usuario.nombre} {nuevo_usuario.primer_apellido}".')


            messages.success(request, 'Usuario registrado exitosamente.')

    # Pasar los perfiles disponibles para el formulario
    perfiles = Perfil.objects.all()

    return render(request, 'usuarios/RegistrarUsuarioAdmin.html', {
        'usuario_actual': usuario_actual,
        'perfiles': perfiles,
    })





#####-------------------------------------------------------------------------------
#####-------------------------------------------------------------------------------
#####-------------------------------------------------------------------------------
##### FUNCIONES DEL METODO DE PAGOOOO


def detalle_compra_cliente(request, venta_id):
    # Obtener el usuario autenticado para la navbar
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.get(pk=usuario_id) if usuario_id else None

    # Codigo para que el numero del carrito funcione
    total_productos = contar_productos_carrito(usuario_id)

    # Obtener los detalles de la venta específica
    venta = get_object_or_404(Venta, pk=venta_id)
    detalles = DetalleVenta.objects.filter(venta=venta)

    # Pasar la información a la plantilla
    return render(request, 'ventas/detalle_venta_cliente.html', {
        'venta': venta,
        'detalles': detalles,
        # Pasar el usuario autenticado
        'usuario': usuario,  

        # Para que el numero del carrito en el nav funcione 
        'total_productos': total_productos,
    })




# usuario_id = request.session.get('usuario_id')

# para que numero del carrito en el nav funcione
# total_productos = contar_productos_carrito(usuario_id)

# return render(request, 'usuarios/PerfilCliente.html', {
#     'usuario': usuario,
#     'total_productos': total_productos,  # Agregar el total de productos al contexto
# })

def agregar_metodo_pago(request):
    usuario_id = request.session.get('usuario_id')

    if not usuario_id:
        return redirect('iniciar_sesion')  # Redirigir si no está autenticado

    total_productos = contar_productos_carrito(usuario_id)  # Usar la función auxiliar para calcular

    if request.method == 'POST':
        # Obtener datos del formulario
        nombre = request.POST.get('nombre')
        tipo_tarjeta = request.POST.get('tipo_tarjeta')
        numero_tarjeta = request.POST.get('numero_tarjeta')
        fecha_expiracion = request.POST.get('fecha_expiracion')
        cvv = request.POST.get('cvv')

        if not nombre:
            messages.error(request, 'El nombre del método de pago es obligatorio.')
        else:
            # Crear el método de pago
            MetodoPago.objects.create(
                usuario_id=usuario_id,
                nombre=nombre,
                tipo_tarjeta=tipo_tarjeta,
                numero_tarjeta=numero_tarjeta,
                fecha_expiracion=fecha_expiracion,
                cvv=cvv,
                habilitado=True
            )
            messages.success(request, 'Método de pago agregado exitosamente.')
            return redirect('ver_metodos_pago')  # Cambiar al nombre de la página donde se muestran los métodos

    return render(request, 'compras/agregar_metodo_pago.html', {
        'total_productos': total_productos,  # Pasar el total de productos al contexto
    })





def guardar_metodo_pago(request):
    if request.method == 'POST':
        usuario_id = request.session.get('usuario_id')
        
        if not usuario_id:
            messages.error(request, "Debes iniciar sesión para agregar un método de pago.")
            return redirect('iniciar_sesion')

        nombre = request.POST.get('nombre')
        tipo_tarjeta = request.POST.get('tipo_tarjeta')
        numero_tarjeta = request.POST.get('numero_tarjeta')
        fecha_expiracion = request.POST.get('fecha_expiracion')  # Formato esperado: 'YYYY-MM'
        cvv = request.POST.get('cvv')

        # Validar que todos los campos necesarios estén presentes
        if not all([nombre, tipo_tarjeta, numero_tarjeta, fecha_expiracion, cvv]):
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, 'compras/agregar_metodo_pago.html')

        # Guardar el método de pago
        metodo_pago = MetodoPago(
            usuario_id=usuario_id,
            nombre=nombre,
            tipo_tarjeta=tipo_tarjeta,
            numero_tarjeta=numero_tarjeta,
            fecha_expiracion=fecha_expiracion,  # Directamente usando el valor del formulario
            cvv=cvv
        )

        try:
            metodo_pago.save()

            usuario_actual = Usuario.objects.get(pk=request.session.get('usuario_id'))
            registrar_accion(usuario_actual, 'Agregar', 'MétodoPago', metodo_pago.metodo_pago_id, f'El usuario "{usuario_actual.nombre} {usuario_actual.primer_apellido}" agregó un método de pago llamado "{nombre}".')

            messages.success(request, "Método de pago guardado exitosamente.")
            return redirect('listar_metodo_pago')
        except Exception as e:
            messages.error(request, "Ocurrió un error al guardar el método de pago: " + str(e))
            return render(request, 'compras/agregar_metodo_pago.html')

    return render(request, 'compras/agregar_metodo_pago.html')





def listar_metodo_pago(request):
    usuario_id = request.session.get('usuario_id')
    
    if not usuario_id:
        # Manejo de caso en que el usuario no esté autenticado
        return redirect('login')  # Ajusta esto al nombre de tu vista de inicio de sesión
    
    total_productos = contar_productos_carrito(usuario_id)
    
    # Filtrar métodos de pago asociados al usuario conectado y habilitados
    metodos_pago = MetodoPago.objects.filter(usuario_id=usuario_id, habilitado=True)
    
    return render(request, 'compras/listar_metodo_pago.html', {
        'metodos_pago': metodos_pago,
        'total_productos': total_productos
    })


def deshabilitar_metodo_pago(request, metodo_pago_id):
    if request.method == 'POST':
        metodo_pago = get_object_or_404(MetodoPago, pk=metodo_pago_id)
        metodo_pago.habilitado = False  # Cambia el estado a deshabilitado
        metodo_pago.save()  # Guarda los cambios
        usuario_actual = Usuario.objects.get(pk=request.session.get('usuario_id'))
        registrar_accion(usuario_actual, 'Deshabilitar', 'MétodoPago', metodo_pago.metodo_pago_id, f'El usuario "{usuario_actual.nombre} {usuario_actual.primer_apellido}" deshabilitó el método de pago llamado "{metodo_pago.nombre}".')
        return redirect('listar_metodo_pago')  # Redirige a la lista de métodos de pago
    else:
        return redirect('listar_metodo_pago')  # Redirige si no es POST











def venta_exitosa(request, venta_id):
    # Obtén la venta utilizando el ID de la venta
    venta = get_object_or_404(Venta, venta_id=venta_id)
    return render(request, 'compras/venta_exitosa.html', {'venta': venta})




def realizar_pago(request):
    if request.method == 'POST':
        # Obtiene el usuario_id de la sesión
        usuario_id = request.session.get('usuario_id')

        if not usuario_id:
            return redirect('login')  # Redirigir si no hay usuario_id

        # Usa el campo correcto para obtener el usuario
        usuario = get_object_or_404(Usuario, usuario_id=usuario_id)  # Usa usuario_id en lugar de id

        metodo_pago = request.POST.get('metodo_pago')
        metodo_envio = request.POST.get('metodo_envio')

        # Busca el carrito del usuario
        carrito = get_object_or_404(Carrito, usuario=usuario, estado__nombre_estado='Activo')

        # Obtiene todos los productos en el carrito
        productos_carrito = carrito.productos.all()

        if not productos_carrito.exists():
            return redirect('carrito')

        # Calcula el total del carrito
        total = sum(item.cantidad * item.precio_unitario for item in productos_carrito)

        # Obtiene el estado "Pendiente"
        estado_pendiente = get_object_or_404(EstadoPedido, pk=1)

        # Inicia una transacción
        with transaction.atomic():
            # Crea la venta
            venta = Venta.objects.create(
                usuario=usuario,
                fecha=now().date(),
                total=total,
                estado=estado_pendiente,
            )

            # Crea los detalles de la venta
            for item in productos_carrito:
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=item.producto,
                    cantidad=item.cantidad,
                    precio_unitario=item.precio_unitario,
                )

            # Elimina el carrito y los productos asociados
            productos_carrito.delete()
            carrito.delete()

            usuario_actual = Usuario.objects.get(pk=request.session.get('usuario_id'))
            registrar_accion(usuario_actual, 'Realizar', 'Venta', venta.venta_id, f'El usuario "{usuario_actual.nombre} {usuario_actual.primer_apellido}" realizó un compra de ${total}.')

        # Redirige a una página de confirmación o resumen de la compra
        return redirect('resumen_venta', venta_id=venta.venta_id)
    else:
        return redirect('carrito')


def resumen_venta(request, venta_id):
    venta = get_object_or_404(Venta, pk=venta_id)
    detalles = venta.detalles.all()

    # Calcular el total por detalle y agregarlo al contexto
    for detalle in detalles:
        detalle.total = detalle.cantidad * detalle.precio_unitario

    return render(request, 'ventas/resumen_venta.html', {
        'venta': venta,
        'detalles': detalles
    })




def ver_acciones(request):
    lista_acciones = HistorialAcciones.objects.all().order_by('-fecha')  # Obtener todas las auditorías, ordenadas por fecha
    return render(request, 'usuarios/ver_acciones.html', {'auditoria_list': lista_acciones})



# Función para registrar la auditoría
def registrar_accion(usuario, accion, tabla, registro_id, detalles=''):
    HistorialAcciones.objects.create(
        usuario=usuario,
        accion=accion,
        tabla=tabla,
        registro_id=registro_id,
        detalles=detalles,
    )
