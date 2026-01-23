I have analyzed the current project structure and prepared a comprehensive UI upgrade plan to modernize the application.

# UI Upgrade & Renovation Plan

## 1. Global Visual Style Upgrade (Foundation)
**Goal:** Establish a consistent, modern, and professional design language across the entire application.
*   **Theme Update**: Replace the standard blue theme with a modern **"Deep Indigo & Vibrant Gradient"** theme.
*   **CSS Variables**: Update `src/assets/css/global.scss` to redefine:
    *   **Colors**: New primary colors, secondary accents, and semantic colors (success/warning/error).
    *   **Typography**: Modern font stack with improved readability.
    *   **Shapes**: Increase `border-radius` for softer, friendlier UI elements (Buttons, Cards, Inputs).
    *   **Depth**: Refine `box-shadow` usage to create a subtle hierarchy (Glassmorphism touches).

## 2. Login Page Redesign (Complete Overhaul)
**Goal:** Create a visually striking, immersive login experience that differs significantly from the current split-screen layout.
*   **New Style**: **"Modern Glassmorphism"**.
*   **Implementation**:
    *   **Background**: Full-screen dynamic background (abstract geometric shapes or deep gradient).
    *   **Login Box**: A centered, translucent "glass" card with blur effect.
    *   **Interactions**: Smooth entrance animations for the logo and form fields.
    *   **Layout**: Simplified single-column layout within the card, focusing on the login action.

## 3. Home Page Renovation (Interactive Scroll)
**Goal:** Transform the static grid menu into a dynamic, interactive scrolling experience.
*   **New Layout**: **"Infinite Horizontal Marquee"**.
*   **Behavior**:
    *   Menu items (cards) will scroll horizontally automatically across the screen.
    *   **Hover-to-Pause**: Moving the mouse over a card stops the scrolling instantly for interaction.
    *   **Selection**: Clicking a card navigates to the respective module with a transition.
*   **Visuals**: Larger, more detailed cards with high-quality icons and hover lift effects.

## 4. Global Menu & Component Standardization
**Goal:** Ensure every page feels part of the same cohesive system.
*   **Layout & Sidebar**:
    *   Update `src/layout/index.vue` to match the new color scheme (e.g., dark modern sidebar).
    *   Improve menu item spacing and hover effects.
*   **Common Components**:
    *   **Buttons**: Apply gradients or cleaner flat styles with pill-shapes.
    *   **Cards**: Standardize all `el-card` usage (padding, shadows) in `global.scss`.
    *   **Tables**: Custom styling for Element Plus tables (header backgrounds, striping).
*   **Page Consistency**:
    *   Ensure all module pages (e.g., Project Management, Config) follow the unified `Page Header -> Filter -> Content` structure with consistent spacing.

This plan covers all your requirements: a new login style, a scrolling home page, and a system-wide UI polish.
