# Abastos JBot - Plan del proyecto

## Objetivo

Abastos JBot es un sistema para bodegas del Mercado de Abastos que permite recibir pedidos por WhatsApp, administrar precios diarios, disponibilidad de productos, pedidos, notas de remisiÃ³n y estados de pago.

La primera bodega serÃ¡:

Distribuidora de Chiles HernÃ¡ndez

## MVP inicial

### Panel interno

Debe permitir:

- Entrar con contraseÃ±a.
- Ver pedidos pendientes.
- Ver pedidos completados.
- Ver pedidos en fila.
- Actualizar precios diarios.
- Actualizar disponibilidad.
- Abrir pedidos del dÃ­a.
- Cerrar pedidos del dÃ­a.
- Cambiar folio.
- Cambiar estado del pedido.
- Cambiar estado de pago.

### Productos iniciales

- Serrano
- JalapeÃ±o
- Poblano
- GÃ¼ero
- Caloro
- Chilaca
- Habanero
- Cebolla blanca
- Cebolla morada
- Tomate
- Ajos
- Pimientos de color
- Pimientos verdes
- Perones

### Precios por producto

Cada producto tendrÃ¡:

- Precio kg suelto: menos de 10 kg
- Precio 10 kg o mÃ¡s
- Precio por kg en arpÃ­a / bulto / caja

El precio de arpÃ­a, bulto o caja siempre serÃ¡ precio por kg, no precio total del bulto.

### Disponibilidad

Cada producto puede estar:

- Disponible
- No disponible

Si no estÃ¡ disponible, debe seguir apareciendo en WhatsApp como "No disponible por hoy".

## Flujo de WhatsApp

1. Cliente manda mensaje al bot.
2. Bot pregunta a nombre de quiÃ©n serÃ¡ el pedido.
3. Bot pregunta si el pedido serÃ¡ entregado en una bodega del Mercado de Abastos.
4. Si responde sÃ­:
   - Si el nÃºmero ya tiene bodega guardada, se puede usar esa bodega.
   - Si no tiene bodega guardada, se muestra lista de bodegas conocidas.
   - Si no estÃ¡ en la lista, el cliente escribe el nombre.
   - Bot pide confirmar/corregir la bodega.
5. Si responde no:
   - Pedido queda para recoger en Distribuidora HernÃ¡ndez.
6. Bot muestra productos.
7. Cliente elige producto.
8. Bot muestra opciones de precio:
   - Menos de 10 kg
   - 10 kg o mÃ¡s
   - ArpÃ­a/bulto/caja
9. Cliente escribe cantidad.
10. Bot agrega producto al carrito.
11. Bot pregunta si desea agregar otro producto.
12. Cliente puede repetir el proceso.
13. Cliente cierra pedido.
14. Bot muestra resumen.
15. Cliente confirma o modifica.
16. Al confirmar:
   - Se genera folio.
   - Se guarda pedido.
   - Se calcula total si hay precios activos.
   - Se imprime nota si pedidos estÃ¡n abiertos.
   - Se confirma por WhatsApp.

## Pedidos fuera de horario

El panel tendrÃ¡ botÃ³n manual para cerrar pedidos del dÃ­a.

Cuando pedidos estÃ¡n cerrados:

- WhatsApp sigue recibiendo pedidos.
- Los pedidos quedan en fila.
- No se imprimen.
- No se mandan a surtir.
- No llevan precios definitivos.
- Cuando se actualicen precios o se confirme que son iguales, se liberan.

## Estados de pedido

- Pendiente
- Listo
- Completado
- Cancelado

## Estados de pago

- Pendiente
- Pagado
- Abonado
- Fiado

## Funciones posteriores

No van en el MVP, pero se dejan consideradas:

- Cancelar pedidos desde WhatsApp.
- OCR para comprobantes de transferencia.
- Pantalla para cargadores.
- Asignar cargador a pedido.
- Varias bodegas activas.
- Panel maestro para dueÃ±o del sistema.
- Suspender bodega por falta de pago.
- Avisar cuando producto vuelva a estar disponible.


