# Persistencia
La informaci´on por defecto est´a configurada para perdurar en el sistema por
1 semana si no se accede a ella, con fines demostrativos se utiliza 2 min para
evaluar el correcto funcionamiento del sistema, en producci´on se deber´a analizar
la ventana tiempo con la que eliminar los datos, es importante se˜nalar que este
sistema de ficheros est´a dise˜nado para la interacci´on de los distintos nodos de la
red y no como un sistema de persistencia de informaci´on, por lo que se decide
eliminar la informaci´on que no se est´e utilizando para garantizar que nueva
informaci´on puede ser almacenada por los algoritmos que se est´en entrenando.
Este mecanismo se hace efectivo utilizando un thread cuyo ´unico fin es verificar
los timestamps de los ficheros y eliminar los que queden fuera de la ventana de
tiempo predefinida.
