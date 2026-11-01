import os
import pymysql
from flask import Flask, render_template, request, redirect, session, url_for, Response
import folium
from folium.plugins import MarkerCluster
from html import escape
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename 
from dotenv import load_dotenv
from flask import Response
from folium.plugins import MarkerCluster
from html import escape
 
load_dotenv()

app = Flask(__name__)
app.secret_key = "clave_secreta_para_el_proyecto_ambulantes"

# CONFIGURACIÓN DE CARPETA PARA SUBIR FOTOS DE FACHADAS
CARPETA_SUBIDAS = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = CARPETA_SUBIDAS
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

os.makedirs(CARPETA_SUBIDAS, exist_ok=True)

# =========================================================================
# FUNCIÓN AUXILIAR: CONEXIÓN A MYSQL
# =========================================================================
def obtener_conexion_db():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "03Andrepabamo10#"),
        database=os.getenv("DB_NAME", "proyecto_ambulantes"),
        cursorclass=pymysql.cursors.DictCursor
    )


def asegurar_columna_asistencia(cursor):
    """Agrega el estado de venta para instalaciones que ya existían."""
    cursor.execute("SHOW COLUMNS FROM vendedor LIKE 'vendiendo_hoy'")
    if not cursor.fetchone():
        cursor.execute(
            "ALTER TABLE vendedor ADD COLUMN vendiendo_hoy TINYINT(1) NOT NULL DEFAULT 0"
        )

# =========================================================================
# RUTA 1: BIENVENIDA PRINCIPAL
# =========================================================================
@app.route("/")
def index():
    return render_template("index.html")

# =========================================================================
# RUTA 2: EL MAPA (ACCESIBLE AL SELECCIONAR CLIENTE)
# =========================================================================
@app.route("/mapa_clientes")
def mapa():
    mapa_ambulantes = folium.Map(
        location=[4.142, -73.626],
        zoom_start=14,
        tiles="OpenStreetMap"
    )

    vendedores = []
    conexion = None

    try:
        conexion = obtener_conexion_db()
        with conexion.cursor() as cursor:
            # Compatibilidad con bases de datos que todavía no tengan la columna.
            cursor.execute("SHOW COLUMNS FROM vendedor LIKE 'vendiendo_hoy'")
            if not cursor.fetchone():
                cursor.execute(
                    "ALTER TABLE vendedor "
                    "ADD COLUMN vendiendo_hoy TINYINT(1) NOT NULL DEFAULT 0"
                )

            cursor.execute("""
                SELECT id, nombre_puesto, tipo_negocio, latitud, longitud,
                       horario, telefono, url_foto_puesto, vendiendo_hoy
                FROM vendedor
                WHERE estado = 1
                  AND latitud IS NOT NULL AND longitud IS NOT NULL
                  AND latitud BETWEEN -90 AND 90
                  AND longitud BETWEEN -180 AND 180
            """)
            vendedores = cursor.fetchall()
    except Exception as e:
        print(f"Error al cargar vendedores en el mapa: {e}")
    finally:
        if conexion:
            conexion.close()

    marcadores = MarkerCluster(
        name="Puestos registrados",
        disableClusteringAtZoom=17
    ).add_to(mapa_ambulantes)

    puntos_mapa = []

    for v in vendedores:
        try:
            latitud = float(v["latitud"])
            longitud = float(v["longitud"])
        except (TypeError, ValueError):
            continue

        puntos_mapa.append([latitud, longitud])

        nombre = escape(str(v.get("nombre_puesto") or "Puesto"))
        tipo = escape(str(v.get("tipo_negocio") or "Puesto"))
        horario = escape(str(v.get("horario") or "No informado"))
        telefono = escape(str(v.get("telefono") or "No informado"))

        esta_vendiendo = bool(v.get("vendiendo_hoy"))
        texto_estado = (
            "🟢 Está vendiendo"
            if esta_vendiendo
            else "🔴 No salió a vender"
        )
        color_estado = "#188038" if esta_vendiendo else "#d93025"

        imagen_html = ""
        if v.get("url_foto_puesto"):
            foto = escape(str(v["url_foto_puesto"]), quote=True)
            imagen_html = (
                f'<img src="/static/uploads/{foto}" '
                'style="width:100%; max-height:110px; object-fit:cover; '
                'border-radius:6px; margin-bottom:8px;">'
            )

        contenido_html = f"""
            <div style="font-family:Arial,sans-serif; font-size:14px; min-width:190px;">
                {imagen_html}
                <h4 style="margin:0 0 3px; font-size:16px;">
                    <a href="/menu/{v['id']}"
                       style="color:#1a73e8; text-decoration:none; font-weight:bold;">
                        {nombre}
                    </a>
                </h4>
                <span style="font-size:11px; background:#e8f0fe; color:#1a73e8;
                    padding:2px 6px; border-radius:4px; font-weight:bold;">
                    {tipo}
                </span>
                <div style="display:inline-block; margin:8px 0 2px; padding:4px 7px;
                    border-radius:12px; color:white; background:{color_estado};
                    font-size:11px; font-weight:bold;">
                    {texto_estado}
                </div>
                <div style="margin-top:8px;">
                    <strong>⏰ Horario:</strong> {horario}<br>
                    <strong>📞 Contacto:</strong> {telefono}
                </div>
                <hr style="border:0; border-top:1px solid #ddd; margin:10px 0;">
               <button type="button"
        onclick="abrirRutaPuesto({latitud}, {longitud})"
        style="background:#1a73e8; color:white; padding:6px 12px;
               border:0; cursor:pointer; border-radius:4px;
               font-size:12px; font-weight:bold; width:100%;">
    🗺️ Cómo llegar
</button>
            </div>
        """

        folium.Marker(
            location=[latitud, longitud],
            popup=folium.Popup(contenido_html, max_width=300),
            tooltip=nombre,
            icon=folium.Icon(color="red", icon="store", prefix="fa")
        ).add_to(marcadores)

    if puntos_mapa:
        mapa_ambulantes.fit_bounds(
            puntos_mapa,
            padding=[30, 30],
            max_zoom=16
        )

    boton_inicio = """
    <div style="position:fixed; top:16px; right:16px; z-index:9999;
        display:flex; align-items:center; gap:14px; padding:12px 16px;
        max-width:calc(100vw - 32px); background:rgba(255,255,255,.96);
        border:1px solid #e2e9e2; border-radius:15px;
        box-shadow:0 8px 24px rgba(20,55,34,.16); font-family:Arial,sans-serif;">
        <span style="font-size:22px;">🏪</span>
        <span style="line-height:1.25;">
            <strong style="display:block;color:#173c2a;font-size:14px;">Ambulantes Villavicencio</strong>
            <small style="color:#718078;font-size:11px;">Encuentra algo rico cerca</small>
        </span>
        <a href="/" style="display:inline-block; background:#176b45; color:white;
        padding:9px 12px; border-radius:9px; text-decoration:none;
        font-size:12px; font-weight:bold; white-space:nowrap;">Inicio</a>
    </div>
    """
    estilo_mapa = """
    <style>
        .leaflet-popup-content-wrapper { border-radius:14px !important; box-shadow:0 10px 30px rgba(20,55,34,.18) !important; }
        .leaflet-popup-content { margin:14px !important; }
        .leaflet-control-zoom a { color:#176b45 !important; }
        @media(max-width:520px) {
            .leaflet-control-attribution { font-size:9px !important; }
            .leaflet-popup-content { max-width:250px !important; }
        }
    </style>
    """
    javascript_rutas = """
<script>
window.abrirRutaPuesto = function(destLat, destLon) {
    if (!navigator.geolocation) {
        alert("Este navegador no permite obtener la ubicación.");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        function(posicion) {
            const origen =
                posicion.coords.latitude + "," + posicion.coords.longitude;
            const destino = destLat + "," + destLon;

            const url =
                "https://www.google.com/maps/dir/?api=1" +
                "&origin=" + encodeURIComponent(origen) +
                "&destination=" + encodeURIComponent(destino) +
                "&dir_action=navigate";

            window.location.href = url;
        },
        function(error) {
            if (error.code === 1) {
                alert("Permite el acceso a la ubicación para abrir la ruta.");
            } else {
                alert("No se pudo obtener tu ubicación. Activa el GPS e inténtalo otra vez.");
            }
        },
        {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0
        }
    );
};
</script>
"""

    mapa_ambulantes.get_root().html.add_child(folium.Element(estilo_mapa))
    mapa_ambulantes.get_root().html.add_child(folium.Element(boton_inicio))
    mapa_ambulantes.get_root().html.add_child(folium.Element(javascript_rutas))

    
    respuesta = Response(mapa_ambulantes.get_root().render(), mimetype="text/html")
    respuesta.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return respuesta
# =========================================================================
# RUTA 3: VER LOGIN
# =========================================================================
@app.route("/login", methods=["GET"])
def vista_login():
    return render_template("login.html", error=None)

# =========================================================================
# RUTA 4: PROCESAR INICIO DE SESIÓN
# =========================================================================
@app.route("/login", methods=["POST"])
def procesar_login():
    nombre_puesto = request.form.get("nombre_puesto")
    contrasena_plana = request.form.get("contrasena")

    try:
        conexion = obtener_conexion_db()
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id, nombre_puesto, contrasena, url_foto_puesto FROM vendedor WHERE nombre_puesto = %s;", (nombre_puesto,))
            vendedor = cursor.fetchone()

            if vendedor and check_password_hash(vendedor['contrasena'], contrasena_plana):
                session['vendedor_id'] = vendedor['id']
                session['vendedor_nombre'] = vendedor['nombre_puesto']
                session['vendedor_foto'] = vendedor['url_foto_puesto']
                return redirect("/panel")
            else:
                return render_template("login.html", error="El nombre del puesto o la contraseña no coinciden.")
    except Exception as e:
        return f"<h3>❌ Error en el sistema de login:</h3> {e}"
    finally:
        if 'conexion' in locals(): conexion.close()

# =========================================================================
# RUTA 5: DASHBOARD DE CONTROL PRIVADO
# =========================================================================
@app.route("/panel")
def panel_vendedor():
    if "vendedor_id" not in session:
        return redirect("/login")

    productos = []
    categorias = []
    asistencia = False
    conexion = None

    try:
        conexion = obtener_conexion_db()

        with conexion.cursor() as cursor:
            # Consultar productos del vendedor
            cursor.execute("""
                SELECT
                    p.id,
                    p.nombre_p,
                    p.descripcion,
                    p.precio,
                    c.nombre AS categoria
                FROM productos p
                LEFT JOIN categorias c ON p.id_categoria = c.id
                WHERE p.id_vendedor = %s
                ORDER BY p.id DESC
            """, (session["vendedor_id"],))
            productos = cursor.fetchall()

            # Cargar categorías para el selector de productos
            cursor.execute("""
                SELECT id, nombre
                FROM categorias
                WHERE id_vendedor = %s
                ORDER BY nombre ASC
            """, (session["vendedor_id"],))
            categorias = cursor.fetchall()

            # Cargar el estado de venta
            asegurar_columna_asistencia(cursor)
            cursor.execute("""
                SELECT vendiendo_hoy
                FROM vendedor
                WHERE id = %s
            """, (session["vendedor_id"],))
            resultado_asistencia = cursor.fetchone()
            asistencia = bool(
                resultado_asistencia
                and resultado_asistencia.get("vendiendo_hoy")
            )

    except Exception as e:
        print(f"Error al cargar el panel: {e}")

    finally:
        if conexion:
            conexion.close()

    return render_template(
        "panel.html",
        id_vendedor=session["vendedor_id"],
        nombre_vendedor=session["vendedor_nombre"],
        foto_puesto=session.get("vendedor_foto"),
        productos=productos,
        categorias=categorias,
        esta_vendiendo=asistencia
    )

@app.route("/actualizar_asistencia", methods=["POST"])
def actualizar_asistencia():
    if "vendedor_id" not in session:
        return redirect("/login")

    esta_vendiendo = 1 if "1" in request.form.getlist("esta_vendiendo") else 0
    conexion = None

    try:
        conexion = obtener_conexion_db()
        with conexion.cursor() as cursor:
            cursor.execute(
                "UPDATE vendedor SET vendiendo_hoy = %s WHERE id = %s",
                (esta_vendiendo, session["vendedor_id"])
            )
            conexion.commit()

        return redirect("/panel")
    except Exception as e:
        if conexion:
            conexion.rollback()
        return f"<h3>Error al actualizar la asistencia: {e}</h3><a href='/panel'>Volver</a>"
    finally:
        if conexion:
            conexion.close()
# =========================================================================
# RUTA 6: CREAR PRODUCTO
# =========================================================================


@app.route("/guardar_producto", methods=["POST"])
def guardar_producto():

    if 'vendedor_id' not in session:
        return redirect("/login")

    nombre_p = request.form.get("nombre_p", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    precio = request.form.get("precio", "").strip()
    id_categoria = request.form.get("id_categoria", "").strip()

    id_vendedor = session['vendedor_id']
    conexion = None

    if not nombre_p or not precio or not id_categoria:
        return "Debes completar el nombre, el precio y la categoría del producto."

    try:
        precio = float(precio)
        id_categoria = int(id_categoria)

        if precio < 0:
            return "El precio no puede ser negativo."

        conexion = obtener_conexion_db()

        with conexion.cursor() as cursor:

            # Verificar que la categoría pertenezca al vendedor
            cursor.execute("""
                SELECT id
                FROM categorias
                WHERE id = %s AND id_vendedor = %s
            """, (id_categoria, id_vendedor))

            categoria = cursor.fetchone()

            if not categoria:
                return "La categoría seleccionada no es válida para tu negocio."

            # Guardar el producto asociado a la categoría
            cursor.execute("""
                INSERT INTO productos
                (nombre_p, descripcion, precio, id_categoria, id_vendedor)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                nombre_p,
                descripcion,
                precio,
                id_categoria,
                id_vendedor
            ))

            conexion.commit()

        return redirect("/panel")

    except (ValueError, TypeError):
        return "El precio o la categoría no tienen un formato válido."

    except Exception as e:

        if conexion:
            conexion.rollback()

        return f"<h3>Error al guardar el producto: {e}</h3>"

    finally:
        if conexion:
            conexion.close()

# =========================================================================
# RUTA 7: ELIMINAR PRODUCTO POR SU ID
# =========================================================================
@app.route("/eliminar_producto/<int:id_prod>")
def eliminar_producto(id_prod):
    if 'vendedor_id' not in session: 
        return redirect("/login")

    try:
        conexion = obtener_conexion_db()
        with conexion.cursor() as cursor:
            sql = "DELETE FROM productos WHERE id = %s AND id_vendedor = %s;"
            cursor.execute(sql, (id_prod, session['vendedor_id']))
            conexion.commit()
        return redirect("/panel")
    except Exception as e:
        return f"<h3>❌ Error al intentar eliminar de MySQL:</h3> {e}"
    finally:
        if 'conexion' in locals(): conexion.close()

# =========================================================================
# RUTA 8 Y 9: REGISTRO DE VENDEDORES
# =========================================================================
@app.route("/registro")
def vista_registro():
    return render_template("registro.html")

@app.route("/registrar", methods=["POST"])
def procesar_registro():
    nombre_puesto = request.form.get("nombre_puesto")
    tipo_negocio = request.form.get("tipo_negocio") 
    correo = request.form.get("correo")
    telefono = request.form.get("telefono", "").strip()
    contrasena_plana = request.form.get("contrasena", "")
    hora_apertura = request.form.get("hora_apertura", "").strip()
    hora_cierre = request.form.get("hora_cierre", "").strip()
    horario = f"{hora_apertura} - {hora_cierre}"
    latitud = request.form.get("latitud")
    longitud = request.form.get("longitud")

    if not telefono.isdigit() or len(telefono) != 10:
        return "<h3>El teléfono debe tener exactamente 10 números.</h3><a href='/registro'>Volver</a>"

    if not hora_apertura or not hora_cierre:
        return "<h3>Debes indicar la hora de apertura y de cierre.</h3><a href='/registro'>Volver</a>"

    if not contrasena_plana:
        return "<h3>Debes ingresar una contraseña.</h3><a href='/registro'>Volver</a>"

    foto = request.files.get("foto_puesto")
    if not foto or foto.filename == "":
        return "<h3>Debes subir una foto del puesto.</h3><a href='/registro'>Volver</a>"
    
    # LA SECCIÓN CORREGIDA: Perfectamente alineada dentro de la función
    if not latitud or not longitud:
        return "<h3>❌ Error: Captura tu GPS antes de registrarte.</h3><br><a href='/registro'>Volver</a>"

    nombre_limpio = secure_filename(foto.filename)

    if not nombre_limpio:
      return "<h3>El nombre de la foto no es válido.</h3><a href='/registro'>Volver</a>"

    nombre_archivo_foto = f"{telefono}_{nombre_limpio}"
    ruta_guardado = os.path.join(app.config["UPLOAD_FOLDER"], nombre_archivo_foto)
    foto.save(ruta_guardado)

    contrasena_hash = generate_password_hash(contrasena_plana)

    try:
        conexion = obtener_conexion_db()
        with conexion.cursor() as cursor:
            sql = """
                INSERT INTO vendedor (nombre_puesto, tipo_negocio, correo, telefono, contrasena, horario, latitud, longitud, url_foto_puesto)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            cursor.execute(sql, (nombre_puesto, tipo_negocio, correo, telefono, contrasena_hash, horario, latitud, longitud, nombre_archivo_foto))
            conexion.commit()
        return render_template("registro.html", registro_exitoso=True)
    except Exception as e:
        return f"<h3>❌ Error al intentar registrar en MySQL:</h3> {e}"
    finally:
        if 'conexion' in locals(): conexion.close()

# =========================================================================
# RUTA 10: CERRAR SESIÓN
# =========================================================================
# ==========================================
# CREAR CATEGORÍA
# ==========================================

@app.route("/guardar_categoria", methods=["POST"])
def guardar_categoria():
    if 'vendedor_id' not in session:
        return redirect("/login")

    nombre = request.form.get("nombre_categoria", "").strip()
    id_vendedor = session['vendedor_id']

    if not nombre:
        return redirect("/panel")

    conexion = None

    try:
        conexion = obtener_conexion_db()

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT id
                FROM categorias
                WHERE nombre = %s AND id_vendedor = %s
            """, (nombre, id_vendedor))

            categoria = cursor.fetchone()

            if categoria:
                return "Esta categoría ya existe."

            cursor.execute("""
                INSERT INTO categorias (nombre, id_vendedor)
                VALUES (%s, %s)
            """, (nombre, id_vendedor))

            conexion.commit()

        return redirect("/panel")

    except Exception as e:

        if conexion:
            conexion.rollback()

        return f"Error al crear categoría: {e}"

    finally:

        if conexion:
            conexion.close()


@app.route("/actualizar_producto/<int:id_prod>", methods=["POST"])
def actualizar_producto(id_prod):
    if "vendedor_id" not in session:
        return redirect("/login")

    descripcion = request.form.get("descripcion", "").strip()
    precio = request.form.get("precio", "").strip()
    conexion = None

    try:
        precio = float(precio)

        if precio < 0:
            return "El precio no puede ser negativo."

        conexion = obtener_conexion_db()

        with conexion.cursor() as cursor:
            cursor.execute("""
                UPDATE productos
                SET descripcion = %s, precio = %s
                WHERE id = %s AND id_vendedor = %s
            """, (
                descripcion,
                precio,
                id_prod,
                session["vendedor_id"]
            ))

            conexion.commit()

        return redirect("/panel")

    except (ValueError, TypeError):
        return "Escribe un precio válido."

    except Exception as e:
        if conexion:
            conexion.rollback()
        return f"Error al actualizar el producto: {e}"

    finally:
        if conexion:
            conexion.close()

# ==========================================
# EDITAR CATEGORÍA
# ==========================================

@app.route("/editar_categoria/<int:id_categoria>", methods=["POST"])
def editar_categoria(id_categoria):

    if 'vendedor_id' not in session:
        return redirect("/login")

    nuevo_nombre = request.form.get("nombre_categoria", "").strip()
    id_vendedor = session['vendedor_id']

    if not nuevo_nombre:
        return redirect("/panel")

    conexion = None

    try:
        conexion = obtener_conexion_db()

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT id
                FROM categorias
                WHERE nombre = %s
                AND id_vendedor = %s
                AND id != %s
            """, (nuevo_nombre, id_vendedor, id_categoria))

            if cursor.fetchone():
                return "Ya tienes una categoría con ese nombre."

            cursor.execute("""
                UPDATE categorias
                SET nombre = %s
                WHERE id = %s AND id_vendedor = %s
            """, (nuevo_nombre, id_categoria, id_vendedor))

            conexion.commit()

        return redirect("/panel")

    except Exception as e:

        if conexion:
            conexion.rollback()

        return f"Error al editar categoría: {e}"

    finally:

        if conexion:
            conexion.close()

# ==========================================
# ELIMINAR CATEGORÍA
# ==========================================

@app.route("/eliminar_categoria/<int:id_categoria>", methods=["POST"])
def eliminar_categoria(id_categoria):

    if 'vendedor_id' not in session:
        return redirect("/login")

    id_vendedor = session['vendedor_id']
    conexion = None

    try:
        conexion = obtener_conexion_db()

        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM productos
                WHERE id_categoria = %s
                AND id_vendedor = %s
            """, (id_categoria, id_vendedor))

            resultado = cursor.fetchone()

            if resultado['total'] > 0:

                return """
                    <h3>No puedes eliminar esta categoría porque tiene productos asociados.</h3>
                    <a href="/panel">Volver al panel</a>
                """

            cursor.execute("""
                DELETE FROM categorias
                WHERE id = %s AND id_vendedor = %s
            """, (id_categoria, id_vendedor))

            conexion.commit()

        return redirect("/panel")

    except Exception as e:

        if conexion:
            conexion.rollback()

        return f"Error al eliminar categoría: {e}"

    finally:

        if conexion:
            conexion.close()

# RUTA DEL MENÚ PÚBLICO
# RUTA DEL MENÚ PÚBLICO
@app.route("/menu/<int:id_vendedor>")
def menu_cliente(id_vendedor):
    conexion = obtener_conexion_db()
    cursor = conexion.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT *
        FROM vendedor
        WHERE id = %s AND estado = 1
    """, (id_vendedor,))

    vendedor = cursor.fetchone()

    if vendedor is None:
        cursor.close()
        conexion.close()
        return "Vendedor no encontrado"

    cursor.execute("""
        SELECT p.*, c.nombre AS nombre_categoria
        FROM productos p
        LEFT JOIN categorias c ON p.id_categoria = c.id
        WHERE p.id_vendedor = %s
    """, (id_vendedor,))

    productos = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        "menu_cliente.html",
        vendedor=vendedor,
        productos=productos
    )

# RUTA PARA CERRAR SESIÓN
@app.route("/logout")
def cerrar_sesion():
    session.clear()
    return redirect("/")




if __name__ == "__main__":
    app.run(debug=True)









    
