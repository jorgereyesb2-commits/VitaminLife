from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class Perfil(models.Model):
    perfil_id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=30)

    class Meta:
        db_table = 'perfil'


class Usuario(models.Model):
    usuario_id = models.AutoField(primary_key=True)
    rut = models.CharField(max_length=15, unique=True)
    nombre = models.CharField(max_length=20)
    primer_apellido = models.CharField(max_length=20)
    segundo_apellido = models.CharField(max_length=20)
    correo = models.EmailField(max_length=50)
    telefono = models.CharField(max_length=15, blank=True, null=True) 
    contrasena = models.CharField(max_length=128) 
    direccion_envio = models.TextField(blank=True, null=True)
    perfil = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, related_name='usuarios')
    intentos_inicio_sesion = models.IntegerField(default=0)
    cuenta_suspendida = models.BooleanField(default=False)

    class Meta:
        db_table = 'usuario'




class Producto(models.Model):
    producto_id = models.AutoField(primary_key=True)
    sku = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=30)
    descripcion = models.TextField(blank=True, null=True)
    categoria = models.CharField(max_length=30, blank=True, null=True)
    informacion_nutricional = models.TextField(blank=True, null=True)
    dosificacion = models.TextField(blank=True, null=True)
    contenido_envase = models.CharField(max_length=30, blank=True, null=True)
    precio = models.IntegerField()
    imagen_url = models.CharField(max_length=255, blank=True, null=True)
    habilitado = models.BooleanField(default=True)

    class Meta:
        db_table = 'producto'


class Venta(models.Model):
    venta_id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='ventas')
    fecha = models.DateField()
    total = models.IntegerField()
    estado = models.ForeignKey('EstadoPedido', on_delete=models.CASCADE) 

    class Meta:
        db_table = 'venta'


class EstadoPedido(models.Model):
    estado_id = models.AutoField(primary_key=True)
    nombre_estado = models.CharField(max_length=20)

    class Meta:
        db_table = 'estado_pedido'



class DetalleVenta(models.Model):
    detalle_id = models.AutoField(primary_key=True)
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='detalles')
    cantidad = models.IntegerField()
    precio_unitario = models.IntegerField()

    class Meta:
        db_table = 'detalle_venta'



class MetodoEnvio(models.Model):
    envio_id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=30)
    costo = models.IntegerField()
    tiempo_estimado = models.CharField(max_length=20)
    habilitado = models.BooleanField(default=True)

    class Meta:
        db_table = 'metodo_envio'




#############################
###### CARRITO


class Carrito(models.Model):
    carrito_id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name='carritos')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.ForeignKey('EstadoCarrito', on_delete=models.SET_NULL, null=True, related_name='carritos')

    class Meta:
        db_table = 'carrito'

    def __str__(self):
        return f"Carrito de {self.usuario.nombre}"


class ProductoCarrito(models.Model):
    producto_carrito_id = models.AutoField(primary_key=True)
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='productos')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE, related_name='carritos')
    cantidad = models.IntegerField()
    precio_unitario = models.IntegerField()  # Guardar el precio del producto al momento de agregarlo al carrito

    class Meta:
        db_table = 'producto_carrito'

    def __str__(self):
        return f"{self.producto.nombre} en carrito"


class EstadoCarrito(models.Model):
    estado_carrito_id = models.AutoField(primary_key=True)
    nombre_estado = models.CharField(max_length=20)

    class Meta:
        db_table = 'estado_carrito'

    def __str__(self):
        return self.nombre_estado




#######################################################################
##### METODO DE PAGO

class MetodoPago(models.Model):
    metodo_pago_id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='metodos_pago')
    nombre = models.CharField(max_length=30)
    tipo_tarjeta = models.CharField(
        max_length=20,
        choices=[
            ('Visa', 'Visa'),
            ('MasterCard', 'MasterCard'),
            ('Amex', 'American Express'),
            ('Discover', 'Discover'),
            ('Otro', 'Otro'),
        ],
        blank=False,
        null=False
    )
    numero_tarjeta = models.CharField(max_length=16)  # Asegúrate de ajustar el tamaño según sea necesario
    fecha_expiracion = models.CharField(max_length=7)  # Formato YYYY-MM
    cvv = models.CharField(max_length=4)  # O usar un CharField según tus necesidades
    habilitado = models.BooleanField(default=True)

    class Meta:
        db_table = 'metodo_pago'

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_tarjeta_display()})"



class HistorialAcciones(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)  # Cambia a Usuario si ese es tu modelo
    accion = models.CharField(max_length=50)
    tabla = models.CharField(max_length=50)
    registro_id = models.IntegerField()
    detalles = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'historial_acciones'

    def __str__(self):
        return f"{self.fecha} - {self.usuario} - {self.accion}"
