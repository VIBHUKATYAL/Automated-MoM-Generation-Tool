brary
/
design.md



Design System --- Glassmorphic Study Dashboard
1. Design Direction
The interface should follow the visual language of the provided
reference image:

Premium, minimal, calm, study/productivity-focused UI.

Soft glassmorphism rather than heavy or exaggerated glass effects.

A pale blue/lavender atmospheric background with subtle depth.

Large rounded cards with translucent white surfaces.

Strong black typography and black primary CTAs.

Generous whitespace and compact information hierarchy.

Very subtle borders, shadows, and blur.

The interface should feel like a polished modern mobile productivity
app, not a generic dashboard.

The design should prioritize clarity, calmness, and focus.

2. Color Palette
Primary Background
Use a soft blue-to-lavender atmospheric background.

--background-start: #B9E4F2;
--background-mid: #C8DDF3;
--background-end: #D9D4F0;
The background can use a very subtle radial/linear gradient rather than
a flat color.

Example:

background:
  radial-gradient(circle at 20% 10%, rgba(255,255,255,0.35), transparent 35%),
  linear-gradient(145deg, #B9E4F2 0%, #C8DDF3 48%, #D9D4F0 100%);
Glass Surface
--glass: rgba(255, 255, 255, 0.58);
--glass-strong: rgba(255, 255, 255, 0.72);
--glass-border: rgba(255, 255, 255, 0.62);
Glass surfaces should remain translucent so the atmospheric background
is still visible.

Text
--text-primary: #111111;
--text-secondary: #66676D;
--text-muted: #92939A;
Use near-black rather than pure black for normal text.

Accent
The design does not need a large colorful accent system. Keep the
interface mostly monochrome on top of the blue/lavender background.

--accent: #111111;
--accent-soft: rgba(17,17,17,0.08);
Status Colors
Use status colors sparingly.

--success: #55B889;
--warning: #E8B85C;
--danger: #E46F6F;
Status colors should appear mainly in small indicators, progress states,
or badges.

3. Glassmorphism Rules
Glassmorphism is the defining visual characteristic.

Glass Card
background: rgba(255, 255, 255, 0.58);
backdrop-filter: blur(24px);
-webkit-backdrop-filter: blur(24px);
border: 1px solid rgba(255, 255, 255, 0.62);
box-shadow:
  0 12px 35px rgba(70, 80, 110, 0.10),
  inset 0 1px 0 rgba(255,255,255,0.45);
Important
Do NOT make every element glass.

Use glass primarily for:

Main cards

Navigation containers

Progress cards

Calendar cards

Modal/dialog surfaces

Large information panels

Buttons, text, and small controls should remain visually simple.

Glass Should Feel Soft
Avoid:

Excessive blur

Strong white borders

Heavy drop shadows

Very transparent cards that become unreadable

Neon gradients

Excessive reflections

The reference has a soft frosted-glass effect, not a futuristic
cyberpunk glass effect.

4. Border Radius
Use large, friendly rounded corners.

--radius-xs: 10px;
--radius-sm: 14px;
--radius-md: 20px;
--radius-lg: 28px;
--radius-xl: 34px;
Recommended:

Buttons: 14–18px

Small cards: 18–22px

Main cards: 24–30px

Main dashboard container: 28–34px

Avoid sharp corners.

5. Typography
Typography should be clean and modern.

Preferred fonts:

Inter

SF Pro Display / SF Pro Text

Geist

Manrope

Use one font family consistently.

Hierarchy
Page title
24–30px
Weight: 650–750

Section title
16–20px
Weight: 600–700

Card title
15–18px
Weight: 600–700

Body
13–15px
Weight: 400–500

Metadata
11–13px
Weight: 400–500
The reference uses strong black headings with small gray supporting
text.

Do not use excessive font sizes.

6. Layout Philosophy
The layout should feel like a mobile-first productivity application.

Desktop
Use a centered application shell with generous margins.

┌─────────────────────────────────────────────┐
│                                             │
│        Atmospheric blue/lavender bg         │
│                                             │
│    ┌───────────────────────────────────┐    │
│    │ Header                            │    │
│    │                                   │    │
│    │ ┌─────────────────────────────┐   │    │
│    │ │ Main Focus / Hero Card      │   │    │
│    │ │                             │   │    │
│    │ └─────────────────────────────┘   │    │
│    │                                   │    │
│    │ ┌────────────┐ ┌──────────────┐   │    │
│    │ │ Progress   │ │ Calendar     │   │    │
│    │ └────────────┘ └──────────────┘   │    │
│    └───────────────────────────────────┘    │
│                                             │
└─────────────────────────────────────────────┘
Mobile
Cards should stack vertically.

The interface should preserve the visual rhythm of the reference image.

7. Main Hero / Focus Card
The most important card should visually dominate the page.

It should contain:

Small context label

Main title

Short description

Primary action

Optional progress/status indicator

Example:

Today's focus

Study Typography
Fundamentals

Learn about font pairing, hierarchy and
readability. Complete the typography
exercise in your design notebook.

[ Start Task  1 hour ]
Hero Card Styling
padding: 24px;
border-radius: 28px;
background: rgba(255,255,255,0.68);
backdrop-filter: blur(26px);
The title should be black and visually dominant.

8. Primary Button
The reference uses a strong black pill/button against the light glass
card.

background: #111111;
color: #FFFFFF;
border-radius: 999px;
padding: 12px 20px;
font-weight: 600;
Hover:

transform: translateY(-1px);
box-shadow: 0 8px 18px rgba(0,0,0,0.15);
Active:

transform: scale(0.98);
Keep the animation subtle.

9. Progress Indicator
Progress should be visually lightweight.

Example:

Overall progress                         35%

██████████████░░░░░░░░░░░░░░░░░░
Use:

Thin progress track

Rounded progress fill

Small percentage label

No excessive gradients

A circular progress indicator can be used in compact headers.

10. Calendar / Timeline
The calendar should feel integrated into the glass surface.

Example:

This week

  2    3    4    5    6    7
       ○    ●    ○    ○    ○
The active day should use a soft white/bright circular highlight.

Avoid traditional spreadsheet-style calendars.

11. Cards
Cards should have a clear hierarchy.

Standard Card
background: rgba(255,255,255,0.52);
backdrop-filter: blur(22px);
border: 1px solid rgba(255,255,255,0.60);
border-radius: 24px;
padding: 20px;
Card Hierarchy
Small metadata
↓
Card title
↓
Supporting information
↓
Action / status
Do not overcrowd cards.

12. Navigation
Navigation should be minimal.

Possible structure:

Home     Tasks     Progress     Profile
On mobile, use a floating/translucent bottom navigation.

background: rgba(255,255,255,0.58);
backdrop-filter: blur(24px);
border: 1px solid rgba(255,255,255,0.65);
border-radius: 24px;
Active navigation item should use black.

Inactive items should use muted gray.

13. Iconography
Use simple outline icons.

Recommended libraries:

Lucide

Phosphor

SF Symbols where available

Icons should be:

Thin/medium weight

Monochrome

Rounded

Small

Avoid colorful or 3D icons.

14. Shadows
Shadows must be extremely soft.

Preferred:

box-shadow:
  0 10px 30px rgba(60, 70, 100, 0.08);
For elevated elements:

box-shadow:
  0 18px 45px rgba(60, 70, 100, 0.12);
Never use dark, sharp shadows.

15. Background Decoration
The background can contain very subtle blurred light shapes.

Example:

background:
  radial-gradient(
    circle at 15% 20%,
    rgba(255,255,255,0.40),
    transparent 28%
  ),
  radial-gradient(
    circle at 85% 75%,
    rgba(220,210,255,0.25),
    transparent 30%
  ),
  linear-gradient(
    145deg,
    #B9E4F2,
    #C8DDF3,
    #D9D4F0
  );
Decorative elements should never compete with the content.

16. Spacing System
Use a consistent 4/8px-based spacing system.

4px
8px
12px
16px
20px
24px
32px
40px
48px
64px
Recommended:

Card internal padding: 20--28px

Between card sections: 16--24px

Between major sections: 28--40px

Page padding mobile: 16--20px

Page padding desktop: 32--48px

17. Interaction & Animation
Animations should be calm and fast.

Recommended:

transition: all 180ms ease;
Use:

Slight card lift on hover

Button compression on click

Soft fade/slide when content appears

Progress animation

Subtle navigation transitions

Avoid:

Bouncy animations

Excessive parallax

Large scale animations

Constant moving background effects

The product should feel focused and distraction-free.

18. Responsive Behavior
Mobile
Prioritize:

Today's focus

Primary action

Progress

Upcoming tasks

Calendar

Secondary information

Cards stack vertically.

Tablet
Use a two-column layout where appropriate.

Desktop
Use a centered max-width layout and multiple cards per row.

Recommended maximum content width:

max-width: 1100px;
19. Accessibility
Despite the translucent design:

Maintain readable contrast.

Do not place important text directly over highly detailed
backgrounds.

Use sufficient font size.

Provide visible focus states.

Buttons must have clear labels.

Do not rely only on color to communicate status.

Support reduced-motion preferences.

20. Design Tokens
:root {
  --bg-start: #B9E4F2;
  --bg-mid: #C8DDF3;
  --bg-end: #D9D4F0;

  --glass: rgba(255, 255, 255, 0.58);
  --glass-strong: rgba(255, 255, 255, 0.72);
  --glass-border: rgba(255, 255, 255, 0.62);

  --text-primary: #111111;
  --text-secondary: #66676D;
  --text-muted: #92939A;

  --success: #55B889;
  --warning: #E8B85C;
  --danger: #E46F6F;

  --radius-sm: 14px;
  --radius-md: 20px;
  --radius-lg: 28px;
  --radius-xl: 34px;

  --blur: 24px;

  --shadow-soft:
    0 12px 35px rgba(70, 80, 110, 0.10);
}
21. Overall Visual Rule
The interface should look like a piece of frosted glass floating over
a soft blue/lavender sky.

The visual hierarchy should be:

Atmospheric background → translucent glass cards → black typography →
black primary actions → subtle secondary information.

Do not turn this into a generic blue SaaS dashboard.

The defining characteristics are:

Soft blue/lavender gradient

Frosted translucent surfaces

Large rounded corners

Near-black typography

Black pill-shaped CTA

Minimal icons

Generous whitespace

Soft shadows

Subtle blur

Calm productivity-app aesthetic