# DocForge B2B API

API para generar documentos PDF desde plantillas HTML dinámicas.
Pensada para integraciones B2B.

**URL base:** `https://docforge-b2b-api.onrender.com`

---

## 🔐 Autenticación

Usa una **API Key** en el header `X-API-Key`.
(Ejemplo: `-H "X-API-Key: TU_API_KEY"`)

**¿No tienes API Key?**
1.  Registra tu empresa con `POST /api/v1/organizations`.
2.  Escríbenos a **ondastudiolab@proton.me** para obtenerla.

---

## 📦 Planes y Límites

| Plan | Precio | Documentos/mes |
|------|--------|----------------|
| FREE | $0 | 50 |
| PRO | $19/mes | 5,000 |
| ENTERPRISE | $99/mes | Ilimitado |

[Ver planes y suscribirse →](https://polar.sh/onda-studio-lab)

---

## 📚 Ejemplos de Uso

### Registro de Empresa
```bash
curl -X POST https://docforge-b2b-api.onrender.com/api/v1/organizations \
  -H "Content-Type: application/json" \
  -d '{"name": "Mi Empresa", "email": "email@ejemplo.com"}'
```


### Crear una Plantilla

```bash
curl -X POST https://docforge-b2b-api.onrender.com/api/v1/templates \
  -H "Content-Type: application/json" \
  -H "X-API-Key: TU_API_KEY" \
  -d '{
    "name": "Factura",
    "html_content": "<html>...{{ var }}...</html>",
    "placeholders": "[\"var\"]"
  }'
```
### Generar un PDF

```bash
curl -X POST https://docforge-b2b-api.onrender.com/api/v1/documents/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: TU_API_KEY" \
  -d '{"template_id": 1, "data": {"var": "valor"}}'
```
  
## 📬 Contacto y Soporte

Desarrollado por Onda Studio Lab.
Para consultas, escríbenos a **ondastudiolab@proton.me**.

DocForge B2B · Documentación interactiva en [/docs](https://docforge-b2b-api.onrender.com/docs)
