# Análisis Web: landonorris.com

> Investigación completa del diseño y tecnología de la web oficial de Lando Norris

---

## 1. Stack Tecnológico

| Componente | Tecnología | Notas |
|------------|------------|-------|
| **Plataforma** | Webflow | CMS visual con control total sobre diseño |
| **Animaciones** | GSAP + Webflow Interactions | Animaciones fluidas y profesionales |
| **3D/WebGL** | Canvas WebGL | Casco interactivo en el hero |
| **Tipografía** | Mona Sans + Brier | Variable fonts |

### Scripts detectados
```
https://cdn.snigelweb.com/...
https://assets-global.website-files.com/...  (Webflow CDN)
```

---

## 2. Paleta de Colores

```css
/* Dark Mode Premium */
--background: #0e110c;       /* Verde muy oscuro/casi negro */
--accent-primary: #dbfe01;   /* Amarillo neón/Lima - VELOCIDAD */
--text-primary: #ffffff;
--text-secondary: #8a8a8a;
```

### Psicología del color
- **Verde oscuro**: Naturaleza, calma, profesionalismo
- **Amarillo neón**: Energía, velocidad, innovación, urgencia
- **Contraste extremo**: Premium, exclusivo, high-tech

---

## 3. Tipografía

### Fonts utilizadas

| Uso | Font | Estilo |
|-----|------|--------|
| **Headlines principales** | Brier | Serif elegante, editorial |
| **Cuerpo y UI** | Mona Sans | Sans-serif variable (GitHub) |

### Estrategia tipográfica
- **Serif para autoridad**: Transmite elegancia, prestigio, tradición
- **Sans-serif para funcionalidad**: Modernidad, legibilidad, tecnología
- **Contraste dual**: Crea jerarquía visual clara

### Alternativas gratuitas
- Brier → **Playfair Display** o **Cormorant Garamond**
- Mona Sans → **Inter**, **Satoshi**, **Plus Jakarta Sans**

---

## 4. Elementos de Diseño

### Hero Section
- **Full-screen** con elemento 3D interactivo
- Casco que sigue el movimiento del ratón (WebGL)
- Tipografía oversized
- Navegación minimalista transparente

### Layout
- **Asimétrico "Editorial"**: No sigue grid tradicional
- Imágenes y textos se superponen
- Espacios negativos generosos
- Secciones full-bleed alternadas

### Navegación
- **Hamburger menu** full-screen
- Efecto "tachado" en hover de links
- Transiciones suaves al abrir/cerrar
- Logo fijo con scroll

---

## 5. Animaciones e Interacciones

### Scroll-Triggered Animations
```javascript
// Conceptual - implementar con GSAP o Framer Motion
gsap.from(".element", {
  scrollTrigger: {
    trigger: ".element",
    start: "top 80%",
  },
  opacity: 0,
  y: 50,
  duration: 1,
  ease: "power3.out"
});
```

### Hover Effects
- Links con línea que "tacha" el texto
- Imágenes con zoom sutil
- Botones con glow/brillo

### Parallax
- Capas de fondo se mueven a diferentes velocidades
- Elementos flotantes con movimiento sutil

---

## 6. Screenshots de Referencia

### Hero Section
![Hero](file:///C:/Users/fprada/.gemini/antigravity/brain/5d5a4d23-2ebd-4fe5-a47a-93441d7e7939/lando_norris_hero_section_1769017793867.png)

### Galería de Cascos
![Helmets](file:///C:/Users/fprada/.gemini/antigravity/brain/5d5a4d23-2ebd-4fe5-a47a-93441d7e7939/lando_norris_helmets_cards_1769017825555.png)

### Menú Full-Screen
![Menu](file:///C:/Users/fprada/.gemini/antigravity/brain/5d5a4d23-2ebd-4fe5-a47a-93441d7e7939/lando_norris_menu_open_1769017858917.png)

---

## 7. Librerías Recomendadas para Implementar

### Animaciones
| Librería | Uso | URL |
|----------|-----|-----|
| **GSAP** | Animaciones complejas y timeline | gsap.com |
| **Framer Motion** | React animations | framer.com/motion |
| **Lenis** | Smooth scroll | github.com/studio-freight/lenis |

### 3D/WebGL
| Librería | Uso | URL |
|----------|-----|-----|
| **Three.js** | Escenas 3D completas | threejs.org |
| **React Three Fiber** | Three.js para React | docs.pmnd.rs/react-three-fiber |
| **Spline** | 3D sin código, exportable | spline.design |

---

## 8. Estructura HTML Conceptual

```html
<body class="dark-theme">
  <header class="nav nav--transparent">
    <a class="logo">Brand</a>
    <button class="nav__hamburger">Menu</button>
  </header>

  <section class="hero hero--fullscreen">
    <div class="hero__content">
      <h1 class="hero__title font-serif">
        Headline <span class="accent">Destacado</span>
      </h1>
      <p class="hero__subtitle font-sans">Subtítulo descriptivo</p>
      <a class="btn btn--primary">Call to Action</a>
    </div>
    <div class="hero__visual">
      <canvas id="3d-element"></canvas>
    </div>
  </section>

  <section class="features features--asymmetric">
    <!-- Contenido editorial -->
  </section>

  <nav class="fullscreen-menu" hidden>
    <ul class="menu__list">
      <li><a class="menu__link" href="#">Link 1</a></li>
      <li><a class="menu__link" href="#">Link 2</a></li>
    </ul>
  </nav>
</body>
```

---

## 9. CSS Variables Base

```css
:root {
  /* Colores - Dark Mode */
  --color-bg: #0e110c;
  --color-bg-elevated: #1a1d17;
  --color-accent: #dbfe01;
  --color-accent-hover: #c5e600;
  --color-text: #ffffff;
  --color-text-muted: #8a8a8a;
  
  /* Tipografía */
  --font-serif: 'Playfair Display', Georgia, serif;
  --font-sans: 'Inter', -apple-system, sans-serif;
  
  /* Espaciado */
  --space-xs: 0.5rem;
  --space-sm: 1rem;
  --space-md: 2rem;
  --space-lg: 4rem;
  --space-xl: 8rem;
  
  /* Animaciones */
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-fast: 0.2s;
  --duration-normal: 0.4s;
  --duration-slow: 0.8s;
}
```

---

## 10. Conclusiones Clave

### ¿Por qué funciona este diseño?

1. **Rompe el molde SaaS típico**: No parece una app, parece una revista de lujo
2. **Contraste visual extremo**: Fondo oscuro + acento neón = imposible ignorar
3. **Movimiento con propósito**: Cada animación guía al usuario
4. **Tipografía con personalidad**: Serif + Sans = autoridad + modernidad
5. **Elemento 3D como ancla visual**: Memorable y diferenciador

### Aplicable a cualquier proyecto que quiera transmitir:
- Premium / Exclusivo
- Tecnología avanzada
- Velocidad / Rendimiento
- Marca personal fuerte
- Innovación

---

*Investigación realizada: 21 Enero 2026*
