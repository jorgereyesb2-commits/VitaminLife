from django.urls import path
from django.contrib import admin
from AppVitamin import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.iniciar_sesion, name='iniciar_sesion'),
    path('usuarios/iniciar_sesion/', views.iniciar_sesion, name='iniciar_sesion'),
    path('envios/', views.listar_envios, name='listar_envios'),
    path('envios/crear/', views.crear_envio, name='crear_envio'),
    path('envios/editar/<int:envio_id>/', views.editar_envio, name='editar_envio'),
    path('envios/eliminar/<int:envio_id>/', views.eliminar_envio, name='eliminar_envio'),
    path('envios/toggle_estado/<int:envio_id>/', views.toggle_estado_envio, name='toggle_estado_envio'),
    path('ventas/', views.listar_ventas, name='listar_ventas'),
    path('ventas/detalle/<int:venta_id>/', views.detalle_venta, name='detalle_venta'),
    
    ### PRODUCTOS
    path('productos/', views.listar_productos, name='listar_productos'),
    path('productos/crear/', views.crear_producto, name='crear_producto'),
    path('productos/editar/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('productos/eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
    
    path('', views.productos_inicio, name='productos_inicio'),

    path('productos/<int:producto_id>/', views.ficha_producto, name='ficha_producto'),

    path('productos_cliente/', views.productos_cliente, name='productos_cliente'),

    path('producto/<int:producto_id>/', views.ficha_producto_cliente, name='ficha_producto_cliente'),

    path('ficha_producto/<int:producto_id>/', views.ficha_producto_cliente, name='ficha_producto_cliente'),


    ###CARRITO
    path('carrito/agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/eliminar/<int:producto_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('actualizar_cantidad/<int:producto_id>/<int:cantidad>/', views.actualizar_cantidad, name='actualizar_cantidad'),
    path('resumen_carrito/', views.resumen_carrito, name='resumen_carrito'),
    path('venta_exitosa/<int:venta_id>/', views.venta_exitosa, name='venta_exitosa'),
    path('pago/', views.realizar_pago, name='realizar_pago'),
    path('resumen-venta/<int:venta_id>/', views.resumen_venta, name='resumen_venta'),  # Asegúrate de que esta línea esté presente

    ### METODOS DE PAGO
    path('agregar_metodo_pago/', views.agregar_metodo_pago, name='agregar_metodo_pago'),
    path('listar_metodo_pago/', views.listar_metodo_pago, name='listar_metodo_pago'),
    path('metodos_pago/<int:metodo_pago_id>/deshabilitar/', views.deshabilitar_metodo_pago, name='deshabilitar_metodo_pago'),
    path('guardar_metodo_pago/', views.guardar_metodo_pago, name='guardar_metodo_pago'),

    
    #### USUARIOS
    path('usuarios/', views.registrar_usuario, name='registrar_usuario'),  
    path('usuarios/editar_usuario/<int:usuario_id>/', views.editar_usuario, name='editar_usuario'), 
    path('usuarios/toggle_estado_usuario/<int:usuario_id>/', views.toggle_estado_usuario, name='toggle_estado_usuario'),  
    path('usuarios/toggle_perfil_usuario/<int:usuario_id>/', views.toggle_perfil_usuario, name='toggle_perfil_usuario'), 
    path('usuarios/perfil_cliente/', views.perfil_cliente, name='perfil_cliente'),
    path('usuarios/editar_perfil_cliente/', views.actualizar_perfil_cliente, name='actualizar_perfil_cliente'),
    path('darse_de_baja/', views.darse_de_baja_cliente, name='darse_de_baja_cliente'),

    path('usuarios/perfil_administrador/', views.perfil_administrador, name='perfil_administrador'),
    path('perfil_administrador/actualizar/', views.actualizar_perfil, name='actualizar_perfil'),
    path('usuarios/gestion_usuarios/', views.gestion_usuarios, name='gestion_usuarios'), 
    path('historial_compra/', views.historial_compra, name='historial_compra'),
    path('seguimiento_pedidos/', views.seguimiento_pedidos, name='seguimiento_pedidos'),

    



    path('usuarios/editar_usuario_desde_admin/<int:usuario_id>/', views.editar_usuario_desde_admin, name='editar_usuario_desde_admin'),
    path('usuarios/registrar_usuario_admin/', views.registrar_usuario_admin, name='registrar_usuario_admin'),
    path('ventas/detalle_compra_cliente/<int:venta_id>/', views.detalle_compra_cliente, name='detalle_compra_cliente'),


    # para cambiar estado del producto
    path('productos/toggle_estado/<int:producto_id>/', views.toggle_estado_producto, name='toggle_estado_producto'), 


    path('acciones/', views.ver_acciones, name='ver_acciones'),  # URL para la vista de auditoría
]

