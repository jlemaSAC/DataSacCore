# Cambios Auth

## Cambios realizados

- `POST /auth/login` ya no devuelve `menu`.
- `GET /auth/status` fue eliminado.
- Nuevo endpoint para menu: `GET /auth/menu/data-sac-web`.

## Como usar

### 1. Login

```http
POST /auth/login
```

Entrada:

```json
{
  "codigo": "usuario",
  "clave": "clave"
}
```

Salida:

```json
{
  "puede_ingresar": true,
  "nombre": "Usuario",
  "identificacion": "0000000000",
  "codigo": "usuario",
  "id_agencia": 1,
  "nombre_agencia": "Matriz",
  "activo": true,
  "roles": [],
  "oficinas_consulta": [],
  "token": "jwt",
  "fecha_sistema": "2026-06-16"
}
```

### 2. Menu Data SAC Web

```http
GET /auth/menu/data-sac-web
Authorization: Bearer <token>
```

Entrada:

```http
Authorization: Bearer <token>
```

Salida:

```json
{
  "menu": [
    {
      "label": "AHORROS",
      "routerLink": "/dashboard/ahorros",
      "icon": "pi pi-angle-right",
      "children": [
        {
          "label": "Reportes",
          "routerLink": "/dashboard/ahorros/reportes",
          "icon": "pi pi-file",
          "children": [
            {
              "label": "Créditos Referidos Recaudadores",
              "routerLink": "/dashboard/ahorros/reportes/creditos-referidos-recaudadores",
              "icon": "pi pi-receipt",
              "children": []
            },
            {
              "label": "Cuentas Aperturadas",
              "routerLink": "/dashboard/ahorros/reportes/cuentas-aperturadas",
              "icon": "pi pi-pen-to-square",
              "children": []
            }
          ]
        }
      ]
    }]}
```

## Flujo recomendado

1. Ejecutar `/auth/login`.
2. Guardar el `token`.
3. Ejecutar `/auth/menu/data-sac-web` con `Authorization: Bearer <token>`.
