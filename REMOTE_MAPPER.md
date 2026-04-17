# MoJiTo TV - Remote Control Mapper
# Control Remoto Philco - Mapeo de Teclas

## KeyCodes Registrados (del test)

| KeyCode | Tecla Física | Acción |
|--------|-------------|--------|
| 38     | ↑          | Anterior canal |
| 40     | ↓          | Siguiente canal |
| 37     | ←          | Anterior |
| 39     | →          | Siguiente |
| 13     | ENTER/OK   | Reproducir |
| 33     | PageUp     | Categoría anterior |
| 34     | PageDown  | Categoría siguiente |
| 27     | ESC/BACK  | Cerrar/Stops |

## Problema Conocido

El control remoto de SmartTV (Philco) NO emite eventos de teclado.
Solo emite CLICKS cuando presionas botones.

Solo funciona:
- CLICK con dedo/control en botones
- ENTER en algunos controles

## Código JavaScript para Detectar

```javascript
// Capture todos los inputs
document.addEventListener('keydown', function(e) {
    console.log('keyCode:', e.keyCode);
    console.log('key:', e.key);
    console.log('which:', e.which);
});

// Para SmartTV - solo clicks funcionan
element.addEventListener('click', function(e) {
    console.log('Click en:', e.target);
});
```

## Solución Actual

La interfaz usa ONCLICK para todos los elementos:
- Botones tienen onclick="funcion()"
- Canales tienen onclick="play(index)"
- ENTER keydown como fallback

## Como Agregar Nuevos Controles

1. Agregar onclick en HTML:
   <button onclick="miFuncion()">Texto</button>

2. Agregar handler en keydown:
   document.addEventListener('keydown', function(e) {
       if(e.keyCode === 13) miFuncion();
   });

## Debug en TV

Para ver qué input llega, abre la consola (F12 en PC)
o revisa el archivo ###input### en el servidor.