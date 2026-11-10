# SignTalk Design System

**Status:** Design guidance for the planned React + TypeScript frontend  
**Scope:** Frontend presentation and interaction only. Keep the existing Flask API, MediaPipe/OpenCV processing, SVM model, and recognition behavior unchanged.

## 1. Product and users

SignTalk is a camera-based sign-recognition interface. Its current experience opens a camera, sends captured frames to the Flask prediction endpoint, gathers predictions for a gesture, and presents the resulting label. The current model recognizes a limited set of signs; it is not a general-purpose sign-language translator.

This design supports:

- People who use sign language and want a simple way to try the signs supported by the model.
- People learning sign language who need clear camera setup and recognition feedback.
- People who need a calm, readable interface that does not make them interpret ambiguous controls or status colors.

Treat sign-language users as participants and experts in research and usability testing. Sign languages are distinct languages, and a small set of recognized labels must not be presented as complete translation or as a substitute for human communication.

### Product principles

1. **Make the camera task obvious.** Keep camera setup, live framing, and recognition result as the central workflow.
2. **Be precise about system status.** Distinguish camera permission, frame analysis, gesture completion, and errors.
3. **Set honest expectations.** Name the supported vocabulary and explain recognition limits without overstating accuracy.
4. **Protect visual communication.** Keep the camera region large and uncluttered; do not cover the hands or face with decorative overlays.
5. **Support autonomy.** Explain camera use before permission is requested, and make start, stop, and retry actions clear.
6. **Prefer calm clarity.** Use a restrained palette, consistent spacing, and brief motion only when it helps users understand a state change.

## 2. UI UX Pro Max direction

The bundled UI UX Pro Max design-system search selected **Flat Design**: minimal surfaces, clean lines, typography-led hierarchy, and limited effects. Its accessibility requirements emphasize readable contrast, keyboard access, visible focus, and reduced motion.

For SignTalk, apply this as a **camera-first workspace**, rather than a marketing or feature-heavy landing page:

- Use a warm-white application canvas with simple, clearly bounded cards.
- Use teal for primary actions and meaningful active states; sage for quiet supporting surfaces.
- Keep the camera feed itself visually neutral so hand shape and movement remain easy to see.
- Use small, consistent state transitions rather than animated backgrounds, parallax, or decorative gradients.
- Use vector icons with labels where needed. Do not use emoji or decorative glyphs as the only way to understand a control or status.

## 3. Color palette

Use semantic tokens so components refer to a role rather than a one-off color.

| Token | HEX | Use |
|---|---|---|
| `--color-primary` | `#286F68` | Primary buttons, active navigation, key accents |
| `--color-primary-hover` | `#205B55` | Hover and pressed treatment for primary actions |
| `--color-on-primary` | `#FFFFFF` | Text and icons on primary buttons |
| `--color-teal-soft` | `#D8EAE5` | Quiet teal-tinted supporting surface |
| `--color-sage` | `#E5EEE7` | Calm secondary surface and selected non-primary backgrounds |
| `--color-sage-strong` | `#C9DCCF` | Non-text accents and component boundaries where appropriate |
| `--color-background` | `#FBFAF7` | Warm-white page background |
| `--color-surface` | `#FFFFFF` | Cards, fields, and raised content surfaces |
| `--color-surface-muted` | `#F1F4EF` | Subtle grouped or inset surfaces |
| `--color-text` | `#243331` | Main text and headings |
| `--color-text-muted` | `#5B6A66` | Supporting text, captions, and secondary labels |
| `--color-border` | `#D6DFD9` | Card, input, and divider boundaries |
| `--color-focus` | `#286F68` | Keyboard focus indicator |
| `--color-success` | `#276749` | Success state and status icon |
| `--color-warning` | `#8A571D` | Caution state and status icon |
| `--color-error` | `#A33C36` | Error state, error text, and destructive action |
| `--color-info` | `#315C7A` | Neutral informational state |
| `--color-camera-stage` | `#17231F` | Letterbox/background around the camera image |

### Contrast and color use

The palette was checked for representative text/background pairs. Examples include primary teal on warm white (**5.65:1**), muted text on warm white (**5.44:1**), and main text on white (**13.18:1**). These exceed the WCAG AA 4.5:1 target for normal text. Recheck contrast for every final component state, including opacity, overlays, and disabled styling.

- Use `--color-text` for normal body copy. Do not lighten text to create hierarchy; use size, weight, and spacing.
- Use white text on the primary teal button. Avoid white text on soft teal or sage.
- Use status color together with a text label and, when useful, a distinct icon. Never use color alone.
- Borders and focus indicators must remain visible against the surface they touch.
- This is a light-first palette. A dark theme is not specified; do not generate one by mechanically inverting these tokens.

## 4. Typography

### Font pairing

- **Headings and short emphasis:** Figtree, with a system sans-serif fallback.
- **Body, controls, and longer Vietnamese text:** Noto Sans, with a system sans-serif fallback.

The UI UX Pro Max search recommended this clean, accessible pairing. Noto Sans is appropriate for Vietnamese interface copy; verify the rendered Vietnamese diacritics and available weights in the target browsers. Bundle fonts locally if the deployment should not depend on an external font service.

```css
:root {
  font-family: "Noto Sans", "Segoe UI", sans-serif;
}

h1,
h2,
h3 {
  font-family: "Figtree", "Noto Sans", "Segoe UI", sans-serif;
}
```

### Type scale

Use `rem` units, a comfortable line height, and responsive sizing where headings need to scale.

| Role | Size | Weight | Line height |
|---|---:|---:|---:|
| Page title | `2rem` to `2.5rem` | 650–700 | 1.15 |
| Section title | `1.375rem` | 600–700 | 1.25 |
| Card title | `1.125rem` | 600 | 1.3 |
| Recognition result | `2rem` to `2.75rem` | 650–700 | 1.15 |
| Body | `1rem` | 400 | 1.55 |
| Supporting text | `0.875rem` | 400–500 | 1.5 |
| Labels and metadata | `0.8125rem` minimum | 600 | 1.4 |
| Button text | `0.9375rem` | 600 | 1.2 |

Do not use all-caps or letter-spaced microcopy for important instructions, recognition results, errors, or status messages. Let users zoom without clipping or hiding content.

## 5. Spacing, shape, elevation, and layout

### Spacing scale

Use a 4px base rhythm. Prefer these values over arbitrary gaps:

| Token | Value | Typical use |
|---|---:|---|
| `space-1` | 4px | Icon-to-label gap |
| `space-2` | 8px | Compact control spacing |
| `space-3` | 12px | Related content |
| `space-4` | 16px | Standard component padding |
| `space-6` | 24px | Card sections and form groups |
| `space-8` | 32px | Major content groups |
| `space-12` | 48px | Page-level separation |
| `space-16` | 64px | Large-screen section spacing |

### Shape and elevation

- **Small controls:** 8px radius.
- **Inputs and buttons:** 10px radius.
- **Cards and camera container:** 14px radius.
- **Pills:** fully rounded only for short, compact statuses.
- **Borders:** 1px solid `--color-border`; use a clear border before adding elevation.
- **Shadows:** default to none. If a floating element needs separation, use one soft, low-opacity shadow; do not use layered or colored shadows.
- **Motion:** use a short 150–200ms ease transition for color, opacity, or border changes. Avoid layout-shifting transforms. Honor `prefers-reduced-motion`.
- **Gradients:** not part of the default visual language.

### Layout

- Use a centered, fluid content area with a maximum width around 1440px.
- On wide desktop, use a compact navigation rail or sidebar only if it improves orientation; keep the camera workspace dominant.
- Keep the camera preview and result adjacent on wide screens. Place supporting guidance after the primary task rather than above it.
- Use a single-column content flow when available width cannot support a legible camera preview and result panel side by side.
- Keep consistent page gutters: approximately 32px on desktop, 24px on tablet, and 16px on small mobile.
- Ensure the page can scroll naturally; avoid fixed panels that obscure camera controls, results, or keyboard focus.

## 6. Component styles

### Buttons

- Primary action: solid `--color-primary` background, `--color-on-primary` label, 10px radius, and at least 44px height.
- Secondary action: white or muted surface with a visible border and main-text label.
- Destructive action: use error styling for the label or boundary and require a clear action name (for example, **Stop camera**).
- Provide distinct hover, pressed, disabled, and focus-visible states. Disabled controls must not look active.
- Make the entire control hit area usable; do not rely on a small icon target.
- Use concise verbs: **Start camera**, **Stop camera**, **Continue scanning**.

### Cards

- Use white surfaces, a 1px border, 14px radius, and 20–24px internal padding.
- Keep one clear heading and a predictable content order.
- Avoid nested cards unless they create a meaningful grouping.
- Do not use color or shadow alone to imply interactivity.

### Inputs

The current camera workflow does not require form inputs. If inputs are introduced later, use a visible label, a minimum 44px control height, a clear border, and a visible focus ring. Associate helper and error copy programmatically with the field; do not use placeholder text as the only label.

### Navigation

- Use explicit text labels for primary destinations.
- Expose the current destination with both a visual treatment and a semantic selected/current state.
- If navigation collapses on smaller screens, preserve accessible names and provide a clear, keyboard-operable way to reveal destinations.
- Keep navigation secondary to the camera and recognition task.

## 7. Camera and recognition components

These are presentation components for the existing flow, not new model or backend features.

### Camera workspace

- **Camera panel:** a clear section title, current camera state, preview, and camera controls.
- **Permission introduction:** brief, plain-language explanation before requesting camera access. State that frames are sent to SignTalk's configured Flask server for analysis; do not make unsupported privacy or storage promises.
- **Camera preview:** preserve a useful view of the hands and face. Avoid cropping the user's hands, placing text over the signing area, or using strong decorative frames. A mirrored preview may be used for user comfort, but do not mirror the frame sent to the existing recognition endpoint unless that behavior is already required by the implementation.
- **Framing guidance:** place concise, practical instructions outside the video area; do not rely on overlays that obscure the sign.
- **Controls:** present **Start camera** before permission is granted; present **Stop camera** while active; present **Continue scanning** after the current gesture result when the camera remains active.
- **Live status:** label scanning/recording in text and do not rely on a pulsing dot alone.

### Recognition result

- Show the recognized label as the most prominent text in the result panel.
- Keep detection state and gesture/session status separate from the result label.
- If displaying the frontend's frame agreement percentage, name it as frame agreement/consensus, not model accuracy or confidence.
- Preserve the backend's supported result and error semantics. Do not infer sentence translation, correctness guarantees, or unsupported labels from a single result.
- When a sign is not recognized, use plain, non-blaming language and show a useful next step, such as adjusting hand visibility or trying the gesture again.

## 8. Interaction states and feedback

Use text labels and consistent semantics for every state. The following states map to the current camera and prediction flow.

| State | Presentation | User guidance |
|---|---|---|
| **Ready / empty** | Neutral camera placeholder, concise explanation, primary **Start camera** button; result area says no result is available yet | Explain what starting the camera does |
| **Requesting permission** | Disable the start action and show a short progress label | Tell users to respond to the browser's camera prompt |
| **Permission denied** | Persistent, announced error near the camera controls; keep a clear retry path | Explain how to grant permission in browser settings |
| **Camera unavailable** | Error state in the camera panel; keep the result panel understandable | State that no camera was found or the camera could not start |
| **Scanning / waiting for hand** | Live preview, visible scanning state, concise hand-framing guidance | Distinguish “camera is active” from “hand detected” |
| **Recording gesture** | Text indicates that the gesture is being collected; keep the preview unobstructed | Explain that the user should complete the sign naturally |
| **Analyzing / waiting for response** | Non-blocking progress indication; keep the stop control available | Avoid indefinite or unexplained loading |
| **Recognized / review** | Present the result label and any existing frame-agreement information; offer **Continue scanning** | Make clear the current gesture is complete |
| **Not recognized** | Neutral result state, not a green success state; provide a retry instruction | Do not imply user error or promise that retry will succeed |
| **Prediction/API error** | Announced error with a clear recovery action; preserve the distinction from permission errors | Say analysis failed and whether the camera stopped or can be retried |
| **Stopped** | Preview cleared, camera inactive state shown, start action restored | Confirm the camera has stopped |

### Loading and motion

- Use a small spinner or progress treatment only when an action is actively waiting; pair it with text.
- Do not animate the recognition result continuously.
- Provide a static state when `prefers-reduced-motion: reduce` is enabled.
- Avoid automatic focus changes for routine state updates. Announce important status and error changes with appropriate live-region semantics.

## 9. Responsive behavior

Design and verify at **375px, 768px, 1024px, and 1440px**. These are review widths, not rigid device categories.

### Desktop (approximately 1024px and wider)

- Use a two-column camera/result workspace when both panels remain readable.
- Keep camera preview large enough for hand and face visibility.
- Keep the main action visible near the preview, not separated in distant page chrome.

### Tablet (approximately 768–1023px)

- Reduce outer gutters and sidebar width before shrinking the camera preview excessively.
- Stack result below the camera if side-by-side panels become cramped.
- Keep controls on a single row only while labels and hit areas remain comfortable.

### Mobile (below approximately 768px)

- Use a single-column layout with camera first, result immediately after, and guidance later.
- Use a fluid preview that preserves the source aspect ratio; allow vertical scrolling rather than cropping important signing space.
- Keep controls full-width or comfortably sized, with at least 44px height.
- Avoid icon-only navigation or controls without accessible names.
- Ensure live statuses, errors, and result labels wrap without clipping or horizontal page scrolling.

## 10. Accessibility requirements

- Target **WCAG 2.2 AA** for the frontend.
- Maintain at least **4.5:1** contrast for normal text and **3:1** for large text and meaningful non-text controls/indicators. Verify final rendered states.
- Ensure all functions work with keyboard alone. Use native buttons and links, logical focus order, and a clearly visible `:focus-visible` indicator.
- Keep focus visible and unobscured after actions, especially when errors or results appear.
- Use semantic headings and landmarks. Give camera controls and icon buttons accessible names.
- Announce important scanning, completion, and error updates to assistive technology without flooding it with per-frame updates.
- Do not use color, animation, position, or icon shape as the sole indicator of meaning.
- Pair every error with actionable text. For recoverable errors, provide a retry or clear next step.
- Respect browser zoom and text resizing; do not clip text at 200% zoom.
- Respect `prefers-reduced-motion`. Never make animation necessary to understand a state.
- Provide text equivalents for important instructions and results. Do not assume users can hear audio or that audio output exists.
- Ensure camera use is initiated by a clear user action and that users can stop it.
- Test with keyboard-only navigation, a screen reader, high zoom, reduced motion, narrow screens, and people who use sign language.

## 11. Recommended frontend components

The following React components are a recommended frontend structure, not a claim that they already exist:

1. **`AppShell`** — page landmarks, responsive navigation, and shared layout.
2. **`StudioPage`** — coordinates the camera workspace and recognition result.
3. **`CameraPanel`** — camera preview, permission explanation, framing guidance, and controls.
4. **`CameraPreview`** — video element, empty placeholder, and non-obscuring live status.
5. **`CameraControls`** — start, stop, and continue-scan actions for the existing flow.
6. **`RecognitionResult`** — recognized label, current result description, and existing frame-agreement metadata when available.
7. **`DetectionStatus`** — accessible face/hand detection and scan-state labels.
8. **`StatusMessage`** — reusable loading, success, neutral, and error feedback with appropriate live-region behavior.
9. **`UsageGuide`** — concise setup and signing guidance based on the actual supported vocabulary and documented behavior.

Keep camera stream lifecycle and capture scheduling in a focused hook (for example, `useCamera`); keep the typed request to `/api/predict` in a small API module. Those implementation boundaries must preserve the Flask endpoint and recognition model unchanged.
