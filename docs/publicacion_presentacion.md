# Presentación aislada con fotografías

La presentación usa la misma versión de código que la operación, con base, archivos, usuario de sistema, cuentas y cookies separados. No modifica el modelo ni habilita comparabilidad. El modo público exige activación explícita, clave propia y host, escucha solo en loopback y se publica bajo `/presentacion/` por el proxy HTTPS existente.

`cargar_presentacion` prepara el histórico sintético de 288 servicios y sus recomendaciones. No se sustituyen sus cifras por supuestos resultados del detector. Cocina excluye esos identificadores de la cola del entorno de presentación para evitar abrir ilustraciones de relleno.

`cargar_casos_fotograficos` requiere un paquete privado con fotografías, hashes y una nota de procedencia por caso. Su modo por defecto solo previsualiza. La aplicación explícita exige cuentas activas de Registro y Cocina y los pesos ONNX privados. El resultado pasa por el predictor, la validación de máscaras y las operaciones de dominio habituales. Conserva origen SIMULADO por tratarse de una presentación, aunque la inferencia sí se ejecuta con el modelo. No aprueba geometría ni completa detecciones ausentes como cero.

El primer caso usa una preparación real propia de seco de pollo, completa y con restos. El segundo utiliza el par reservado del simulacro, cuya procedencia visual no se ha validado como una preparación independiente. Las notas se muestran junto al caso. Los dos resultados actuales son no concluyentes; hay fotografías y máscaras, pero no porcentajes válidos inventados.

Repetir la carga con el mismo manifiesto recupera los servicios y análisis existentes, y comprueba las huellas antes de continuar. No sobrescribe imágenes. El comando solo funciona con `config.settings_presentacion`; no debe utilizarse con la base operativa.

En publicación, se utiliza el motor privado existente para las nuevas solicitudes de análisis, sin ampliar la instancia ni iniciar otro modelo. El proceso web y su worker tienen memoria limitada y acceso de escritura solo a sus propios directorios. Las imágenes y los pesos no forman parte del repositorio. Las credenciales de presentación se entregan por separado y no se incluyen en esta guía ni en los paquetes para diseño.

Los accesos iniciales a Indicadores y Comparar abren filtros del histórico de ejemplo para que el recorrido empiece con resultados. El usuario puede desplegar los filtros y cambiarlos. En operación se mantiene el comportamiento normal.
