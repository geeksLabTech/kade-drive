# Persistencia

La información por defecto está configurada para perdurar en el sistema por 1 semana si no se accede a ella. Sin embargo, con fines demostrativos, se utiliza un tiempo de 2 minutos para evaluar el correcto funcionamiento del sistema. En producción, se deberá analizar el intervalo de tiempo para eliminar los datos de acuerdo a los requisitos del sistema.

Es importante tener en cuenta que este sistema de ficheros está diseñado para la interacción de los distintos nodos de la red y no como un sistema de persistencia de información a largo plazo. Por lo tanto, se decide eliminar la información que no se esté utilizando para garantizar que nuevos datos puedan ser almacenados por los algoritmos de entrenamiento.

Este mecanismo de eliminación se hace efectivo mediante un hilo (thread) cuyo único propósito es verificar los timestamps de los ficheros y eliminar aquellos que queden fuera de la ventana de tiempo predefinida.
