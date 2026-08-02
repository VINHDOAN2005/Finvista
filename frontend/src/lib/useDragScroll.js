import { useRef } from "react";


export function useDragScroll() {
  const ref = useRef(null);
  const dragRef = useRef(null);
  const suppressClickUntilRef = useRef(0);

  function onPointerDown(event) {
    if (event.button !== 0 || event.target.closest("button, input, select, a")) return;
    const element = ref.current;
    if (!element || element.scrollWidth <= element.clientWidth) return;
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      scrollLeft: element.scrollLeft,
      moved: false
    };
  }

  function onPointerMove(event) {
    const element = ref.current;
    const drag = dragRef.current;
    if (!element || !drag || drag.pointerId !== event.pointerId) return;
    const deltaX = event.clientX - drag.startX;
    if (Math.abs(deltaX) <= 8) return;
    drag.moved = true;
    element.setPointerCapture?.(event.pointerId);
    element.classList.add("is-dragging");
    element.scrollLeft = drag.scrollLeft - deltaX;
    event.preventDefault();
  }

  function endDrag(event) {
    const element = ref.current;
    const drag = dragRef.current;
    if (!element || !drag) return;
    element.releasePointerCapture?.(drag.pointerId || event.pointerId);
    element.classList.remove("is-dragging");
    if (drag.moved) suppressClickUntilRef.current = Date.now() + 180;
    dragRef.current = null;
  }

  return {
    ref,
    dragProps: {
      onPointerDown,
      onPointerMove,
      onPointerUp: endDrag,
      onPointerCancel: endDrag,
      onPointerLeave: endDrag
    },
    clickAllowed: () => Date.now() >= suppressClickUntilRef.current
  };
}
