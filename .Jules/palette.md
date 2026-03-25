## 2026-03-25 - Sidebar Keyboard Accessibility
**Learning:** `div` elements used as interactive items (like the sidebar history items) lack native keyboard accessibility. Users navigating via keyboard couldn't select history snapshots.
**Action:** Always add `role="button"`, `tabindex="0"`, and `onkeydown` (handling 'Enter' and 'Space') to non-native interactive elements to ensure they are fully accessible. Add `:focus-visible` styles to provide clear visual feedback.
