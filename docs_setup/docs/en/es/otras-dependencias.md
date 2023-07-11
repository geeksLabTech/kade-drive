## Dependencia de MessageSystem

`kade_drive` depende del paquete `MessageSystem` como una dependencia adicional para la comunicación entre los nuevos nodos y la red. `MessageSystem` proporciona un sistema de mensajería utilizando multicast y broadcast, lo que permite un intercambio eficiente de mensajes.

El paquete `MessageSystem` es un paquete separado de Python que debe ser instalado como requisito previo para usar `kade_drive`. Maneja los aspectos de comunicación de bajo nivel necesarios para el funcionamiento de `kade_drive`.

Para instalar `MessageSystem`, puedes utilizar pip. Ejecuta el siguiente comando en tu terminal:

```console
pip install message-system
```

## Uso
Una vez instalado `MessageSystem`, puedes usar kade_drive como se describe en esta documentación. Utilizará automáticamente el paquete `MessageSystem` para la autodetección de nodos.

Nótese que esto no es necesario si se instala utilizando poetry ya que este se encarga de instalar todas las dependencias

## Repositorio

<https://github.com/geeksLabTech/message-system>
