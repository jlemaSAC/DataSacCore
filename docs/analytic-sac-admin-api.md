# API — Analytic Sac Admin y catálogos auxiliares

Contrato de los endpoints de administración del menú bajo **`Analytic Sac -
Admin`** y de los catálogos auxiliares de cargos y roles. `GET /analytic/menu` no se incluye:
pertenece a **`Analytic Sac`** y entrega el menú del usuario final.

Base local: `http://127.0.0.1:8000`  
Cabecera requerida: `Authorization: Bearer <token>`

Todos requieren un JWT válido (`401` si falta o no es válido). Las rutas
`/analytic/*` requieren además el rol activo `001` —ADMINISTRADOR— (`403` en
caso contrario); `/nomina/cargos` solo exige autenticación. Los errores de
esquema son `422` y los de negocio se devuelven como `{ "detail": "..." }`.

## Endpoints

| Método | Ruta | Entrada | Salida |
| --- | --- | --- | --- |
| `GET` | `/analytic/rutas` | `activo?: boolean` | `200 Menu[]` |
| `POST` | `/analytic/rutas` | `MenuCreate` | `201 Menu` |
| `GET` | `/analytic/rutas/arbol` | `activo?: boolean` | `200 MenuTree[]` |
| `GET` | `/analytic/rutas/{id_menu}` | `id_menu: ObjectId` | `200 Menu` |
| `PATCH` | `/analytic/rutas/{id_menu}` | `id_menu`, `MenuUpdate` | `200 Menu` |
| `DELETE` | `/analytic/rutas/{id_menu}` | `id_menu` | `200 MenuDelete` |
| `POST` | `/analytic/permisos` | `PermisoCreate` | `201 Permiso` |
| `POST` | `/analytic/rol-permisos` | `RolPermisoCreate` | `201 RolPermiso` |
| `GET` | `/nomina/cargos` | `activo?: boolean` | `200 Cargo[]` |
| `GET` | `/seguridad/roles` | `activo?: boolean` | `200 Rol[]` |

`activo` omitido devuelve registros activos e inactivos. Los listados planos
de menú se ordenan por `orden`; el árbol ordena cada nivel por `orden` y
`label`.

## Estructuras

`id_menu` e `id_padre` son `ObjectId` de MongoDB en formato hexadecimal de 24
caracteres. Las fechas son ISO 8601 en UTC.

```ts
interface MenuCreate {
  codigo: string;                 // único
  label: string;
  icon?: string | null;
  id_padre?: string | null;       // grupo activo
  tipo: "grupo" | "ruta";
  ruta?: string | null;
  permiso_requerido: string;
  orden: number;                  // >= 1
  activo?: boolean;               // true
  roles_codigo?: string[];        // ["001"]
}

interface MenuUpdate {
  codigo?: string;
  label?: string;
  icon?: string | null;
  id_padre?: string | null;
  tipo?: "grupo" | "ruta";
  ruta?: string | null;
  permiso_requerido?: string;
  orden?: number;
  activo?: boolean;
  roles_codigo?: string[] | null;
}

interface PermisoCreate {
  codigo: string;
  recurso: string;
  modulo_codigo?: string | null;
  accion: string;
  activo?: boolean;               // true
}

interface Permiso extends PermisoCreate {
  id: string;
  created_at: string | null;
  updated_at: string | null;
}

interface RolPermisoCreate {
  rol_codigo: string;
  permiso_codigo: string;
  activo?: boolean;               // true
}

interface RolPermiso extends RolPermisoCreate {
  id: string;
  rol_nombre: string | null;
  created_at: string | null;
  updated_at: string | null;
}

interface Menu extends MenuCreate {
  id: string;
  created_at: string | null;
  updated_at: string | null;
  permisos: Permiso[];
  rol_permisos: RolPermiso[];
}

interface MenuTree {
  id: string;
  codigo: string;
  label: string;
  icon: string | null;
  id_padre: string | null;
  tipo: "grupo" | "ruta";
  ruta: string | null;
  permiso_requerido: string;
  orden: number;
  activo: boolean;
  created_at: string | null;
  updated_at: string | null;
  children: MenuTree[];
}

interface MenuDelete {
  id: string;
  permiso_codigo: string;
  rutas_eliminadas: number;
  permisos_eliminados: number;
  rol_permisos_eliminados: number;
  detail: string;
}

interface Cargo {
  id: number;
  nombre: string;
  activo: boolean;
  es_vinculado: boolean | null;
}

interface Rol {
  codigo: string;
  nombre: string;
  nivel: number;
  activo: boolean;
}
```

## Administración del menú

### Crear y actualizar

Un `grupo` puede tener `ruta` opcional; una `ruta` debe tenerla. Un `id_padre`
debe ser un grupo activo. No se puede asignar un nodo como padre propio, moverlo
bajo un descendiente ni convertir en ruta un grupo con hijos activos.

Al crear un menú, o al modificar `codigo`, `permiso_requerido` o `id_padre`, el
servicio crea o reutiliza el permiso requerido —y el del padre cuando existe—.
Al enviar `roles_codigo` crea o reactiva las relaciones correspondientes; no
elimina relaciones de roles que se omitan. Los roles deben existir y estar
activos. Una lista vacía se normaliza a `["001"]`.

Ejemplo de creación de ruta:

```json
{
  "codigo": "SOLVENCIA",
  "label": "Solvencia",
  "id_padre": "65b2f6f9e8c563b4f1e6a001",
  "tipo": "ruta",
  "ruta": "/analytic/indicadores-financieros/solvencia",
  "permiso_requerido": "analytic.solvencia.ver",
  "orden": 1,
  "roles_codigo": ["001", "010"]
}
```

En `GET /analytic/rutas` y `GET /analytic/rutas/{id_menu}`, `permisos` y
`rol_permisos` se devuelven vacíos. Contienen los elementos procesados en
`POST` y en los `PATCH` que los generen.

### Eliminar

`DELETE /analytic/rutas/{id_menu}` solo admite nodos sin hijos, incluso si los
hijos están inactivos. Elimina el menú, su permiso requerido y las relaciones
rol–permiso de ese permiso.

### Permisos independientes

`POST /analytic/permisos` exige `codigo`, `recurso` y `accion`; esta última se
normaliza a `VER` si se envía como `ver`. `POST /analytic/rol-permisos` exige
un rol activo y un permiso activo. La misma pareja rol–permiso no puede
registrarse dos veces.

Errores habituales: `400` por ID, texto, tipo o jerarquía inválidos; `404` por
menú, padre, rol o permiso inexistente/inactivo; `409` por código duplicado,
relación duplicada o conflicto de jerarquía.

## Catálogos de cargos y roles

`GET /nomina/cargos` consulta `NOMINA.CARGO` y devuelve todos los cargos por
defecto. Use `?activo=true` o `?activo=false` para filtrar; el resultado se
ordena por `nombre` y luego `id`.

```http
GET /nomina/cargos?activo=true
Authorization: Bearer <token>
```

```json
[
  {
    "id": 7,
    "nombre": "ASESOR DE CRÉDITO",
    "activo": true,
    "es_vinculado": false
  }
]
```

`GET /seguridad/roles` devuelve todos los roles de `SEGURIDAD.ROL` por defecto;
acepta el mismo filtro `activo` y se ordena por `nivel`, `nombre` y `codigo`.

```http
GET /seguridad/roles?activo=true
Authorization: Bearer <token>
```

```json
[
  {
    "codigo": "001",
    "nombre": "ADMINISTRADOR",
    "nivel": 1,
    "activo": true
  }
]
```

Swagger: `http://127.0.0.1:8000/docs#/Analytic%20Sac%20-%20Admin` y
`http://127.0.0.1:8000/docs#/N%C3%B3mina`; para roles, consulte
`http://127.0.0.1:8000/docs#/Seguridad`.
