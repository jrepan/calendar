document.addEventListener('DOMContentLoaded', () => {
  const calendarEl = document.getElementById('calendar');
  const monthYearEl = document.getElementById('monthYear');
  const prevBtn = document.getElementById('prevMonth');
  const nextBtn = document.getElementById('nextMonth');

  const today = new Date();
  let currentYear = today.getFullYear();
  let currentMonth = today.getMonth();

  // Use user's locale to generate localized month and weekday names.
  const locale = (navigator && navigator.language) ? navigator.language : 'en-US';
  const monthNames = Array.from({ length: 12 }, (_, m) =>
    new Intl.DateTimeFormat(locale, { month: 'long' }).format(new Date(2020, m, 1))
  );
  const weekdayNames = (() => {
    // Jan 4, 2021 is a Monday — use as a stable Monday base to build Mon..Sun
    const baseTimestamp = Date.UTC(2021, 0, 4);
    const fmt = new Intl.DateTimeFormat(locale, { weekday: 'short' });
    const arr = [];
    for (let i = 0; i < 7; i++) {
      arr.push(fmt.format(new Date(baseTimestamp + i * 24 * 60 * 60 * 1000)));
    }
    return arr;
  })();

  function pad(n) { return String(n).padStart(2, '0'); }
  function ymd(year, monthZeroBased, day) {
    return `${year}-${pad(monthZeroBased+1)}-${pad(day)}`;
  }

  // Events are provided by the server via `window.SERVEREVENTS`.
  function eventsFor(dateKey) {
    const all = (window.SERVEREVENTS && Array.isArray(window.SERVEREVENTS)) ? window.SERVEREVENTS : [];
    return all.filter(e => e.date === dateKey);
  }

  // Helper to create a day cell (prev/current/next months). Returns the cell element.
  function createDayCell(year, month, day, { isOtherMonth = false, allowActions = false } = {}) {
    const cell = document.createElement('div');
    cell.className = 'calendar-day' + (isOtherMonth ? ' inactive other-month' : '');
    const dateKey = ymd(year, month, day);
    cell.setAttribute('data-date', dateKey);

    const num = document.createElement('div');
    num.className = 'day-number';
    num.textContent = day;
    cell.appendChild(num);

    const evWrap = document.createElement('div');
    evWrap.className = 'events';
    const evs = eventsFor(dateKey);

    evs.slice(0,3).forEach(ev => {
      const evEl = document.createElement('div');
      evEl.className = 'event';

      const titleSpan = document.createElement('span');
      titleSpan.className = 'event-title';
      titleSpan.textContent = ev.title;
      evEl.appendChild(titleSpan);

      if (allowActions) {
        const actions = document.createElement('span');
        actions.className = 'event-actions';

        const editBtn = document.createElement('button');
        editBtn.className = 'edit-btn';
        editBtn.type = 'button';
        editBtn.title = 'Edit event';
        editBtn.textContent = '✎';
        editBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          // create inline edit form
          const form = document.createElement('div');
          form.className = 'edit-form';

          const inputTitle = document.createElement('input');
          inputTitle.type = 'text';
          inputTitle.value = ev.title;
          inputTitle.className = 'edit-title';

          const inputDate = document.createElement('input');
          inputDate.type = 'date';
          inputDate.value = dateKey;
          inputDate.className = 'edit-date';

          const saveBtn = document.createElement('button');
          saveBtn.type = 'button';
          saveBtn.className = 'save-btn';
          saveBtn.textContent = 'Save';

          const cancelBtn = document.createElement('button');
          cancelBtn.type = 'button';
          cancelBtn.className = 'cancel-btn';
          cancelBtn.textContent = 'Cancel';

          form.appendChild(inputDate);
          form.appendChild(inputTitle);
          form.appendChild(saveBtn);
          form.appendChild(cancelBtn);

          // replace evEl contents with form
          evEl.innerHTML = '';
          evEl.appendChild(form);

          cancelBtn.addEventListener('click', () => {
            renderCalendar(currentYear, currentMonth);
          });

          saveBtn.addEventListener('click', async () => {
            const newTitle = inputTitle.value.trim();
            const newDate = inputDate.value;
            if (!newTitle || !newDate) { alert('Provide date and title'); return; }
            try {
              const res = await fetch('/edit-event', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_date: dateKey, old_title: ev.title, date: newDate, title: newTitle })
              });
              if (!res.ok) throw new Error('edit failed');
              const updated = await res.json();
              if (window.reloadCalendar) window.reloadCalendar(updated);
            } catch (err) {
              console.error('Edit event failed', err);
              alert('Could not edit event');
              renderCalendar(currentYear, currentMonth);
            }
          });
        });

        const delBtn = document.createElement('button');
        delBtn.className = 'delete-btn';
        delBtn.type = 'button';
        delBtn.title = 'Remove event';
        delBtn.textContent = '×';
        delBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          if (!confirm(`Delete event "${ev.title}" on ${dateKey}?`)) return;
          try {
            const res = await fetch('/delete-event', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ date: dateKey, title: ev.title })
            });
            if (!res.ok) throw new Error('delete failed');
            const updated = await res.json();
            if (window.reloadCalendar) window.reloadCalendar(updated);
          } catch (err) {
            console.error('Delete event failed', err);
            alert('Could not delete event');
          }
        });

        actions.appendChild(editBtn);
        actions.appendChild(delBtn);
        evEl.appendChild(actions);
      }

      evWrap.appendChild(evEl);
    });

    cell.appendChild(evWrap);

    if (evs.length > 0) {
      cell.setAttribute('aria-label', `${day} ${monthNames[month]} ${year}: ${evs.map(e=>e.title).join(', ')}`);
    }
    // Highlight today's date
    const todayKey = ymd(today.getFullYear(), today.getMonth(), today.getDate());
    if (dateKey === todayKey) {
      cell.classList.add('today');
    }

    return cell;
  }

  function renderCalendar(year, month) {
    calendarEl.innerHTML = '';

    monthYearEl.textContent = `${monthNames[month]} ${year}`;

    const first = new Date(year, month, 1);
    // Shift so Monday is the first column: JS.getDay() -> 0=Sun..6=Sat
    const startDay = (first.getDay() + 6) % 7;
    const daysInMonth = new Date(year, month+1, 0).getDate();

    weekdayNames.forEach(w => {
      const el = document.createElement('div');
      el.className = 'calendar-weekday';
      el.textContent = w;
      calendarEl.appendChild(el);
    });

    // Leading days from previous month (show full first week)
    const prevMonthDate = new Date(year, month, 0); // last day of previous month
    const daysInPrevMonth = prevMonthDate.getDate();
    const prevMonthIndex = (month + 11) % 12;
    const prevYear = (month === 0) ? year - 1 : year;
    for (let i = startDay; i > 0; i--) {
      const day = daysInPrevMonth - i + 1;
      const cell = createDayCell(prevYear, prevMonthIndex, day, { isOtherMonth: true, allowActions: false });
      calendarEl.appendChild(cell);
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const cell = createDayCell(year, month, d, { isOtherMonth: false, allowActions: true });
      calendarEl.appendChild(cell);
    }

    // Trailing days from next month to complete last week
    const used = startDay + daysInMonth;
    const trailing = (7 - (used % 7)) % 7;
    const nextMonthIndex = (month + 1) % 12;
    const nextYear = (month === 11) ? year + 1 : year;
    for (let i = 1; i <= trailing; i++) {
      const cell = createDayCell(nextYear, nextMonthIndex, i, { isOtherMonth: true, allowActions: false });
      calendarEl.appendChild(cell);
    }
  }

  // Helper to close any open inline forms
  function closeOpenForms() {
    const existing = document.querySelectorAll('.add-form');
    existing.forEach(n => n.remove());
  }

  // Add click handler to calendar container to open add form when a day is clicked
  calendarEl.addEventListener('click', (e) => {
    const dayEl = e.target.closest('.calendar-day');
    if (!dayEl || dayEl.classList.contains('inactive')) return;
    // Prevent opening form when clicking action buttons inside event
    if (e.target.closest('.event') || e.target.closest('button')) return;

    closeOpenForms();
    const dateKey = dayEl.getAttribute('data-date');

    const form = document.createElement('div');
    form.className = 'add-form';

    const inputDate = document.createElement('input');
    inputDate.type = 'date';
    inputDate.value = dateKey;
    inputDate.className = 'add-date';

    const inputTitle = document.createElement('input');
    inputTitle.type = 'text';
    inputTitle.placeholder = 'Event title';
    inputTitle.className = 'add-title';

    const addBtn = document.createElement('button');
    addBtn.type = 'button';
    addBtn.className = 'add-btn';
    addBtn.textContent = 'Add';

    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'cancel-add-btn';
    cancelBtn.textContent = 'Cancel';

    form.appendChild(inputDate);
    form.appendChild(inputTitle);
    form.appendChild(addBtn);
    form.appendChild(cancelBtn);

    dayEl.appendChild(form);
    inputTitle.focus();

    cancelBtn.addEventListener('click', (ev) => {
      ev.stopPropagation();
      form.remove();
    });

    addBtn.addEventListener('click', async (ev) => {
      ev.stopPropagation();
      const date = inputDate.value;
      const title = inputTitle.value.trim();
      if (!date || !title) { alert('Provide date and title'); return; }
      try {
        const res = await fetch('/add-event', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ date, title })
        });
        if (!res.ok) throw new Error('add failed');
        const updated = await res.json();
        if (window.reloadCalendar) window.reloadCalendar(updated);
      } catch (err) {
        console.error('Add event failed', err);
        alert('Could not add event');
      }
    });
  });

  // Expose a reload function so the page can push updated events and re-render
  window.reloadCalendar = function(newEvents) {
    if (Array.isArray(newEvents)) {
      window.SERVEREVENTS = newEvents;
    }
    renderCalendar(currentYear, currentMonth);
  };

  prevBtn.addEventListener('click', () => {
    currentMonth -= 1;
    if (currentMonth < 0) { currentMonth = 11; currentYear -= 1; }
    renderCalendar(currentYear, currentMonth);
  });
  nextBtn.addEventListener('click', () => {
    currentMonth += 1;
    if (currentMonth > 11) { currentMonth = 0; currentYear += 1; }
    renderCalendar(currentYear, currentMonth);
  });

  renderCalendar(currentYear, currentMonth);
});
