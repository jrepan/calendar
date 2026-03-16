document.addEventListener("DOMContentLoaded", () => {
  const exportBtn = document.getElementById("exportIcs");
  const importBtn = document.getElementById("importBtn");
  const importFile = document.getElementById("importFile");
  const calendarEl = document.getElementById("calendar");
  const monthYearEl = document.getElementById("monthYear");
  const prevBtn = document.getElementById("prevMonth");
  const nextBtn = document.getElementById("nextMonth");

  const today = new Date();
  let currentYear = today.getFullYear();
  let currentMonth = today.getMonth();

  const locale = navigator?.language ? navigator.language : "en-UK";
  const monthNames = Array.from({ length: 12 }, (_, m) =>
    new Intl.DateTimeFormat(locale, { month: "long" }).format(
      new Date(2020, m, 1),
    ),
  );
  const weekdayNames = (() => {
    // Jan 4, 2021 is a Monday — use as a stable Monday base to build Mon..Sun
    const baseTimestamp = Date.UTC(2021, 0, 4);
    const fmt = new Intl.DateTimeFormat(locale, { weekday: "short" });
    const arr = [];
    for (let i = 0; i < 7; i++) {
      arr.push(fmt.format(new Date(baseTimestamp + i * 24 * 60 * 60 * 1000)));
    }
    return arr;
  })();

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function ymd(year, monthZeroBased, day) {
    return `${year}-${pad(monthZeroBased + 1)}-${pad(day)}`;
  }

  function eventsFor(dateKey) {
    const all =
      window.SERVEREVENTS && Array.isArray(window.SERVEREVENTS)
        ? window.SERVEREVENTS
        : [];
    return all.filter((e) => e.date <= dateKey && (e.end_date || e.date) >= dateKey);
  }

  exportBtn.addEventListener("click", () => {
    window.location = "/events";
  });

  importBtn.addEventListener("click", () => {
    importFile.click();
  });

  importFile.addEventListener("change", async (ev) => {
    const file = ev.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch("/events", { method: "PUT", body: form });
      let body = null;
      try {
        body = await res.json();
      } catch (e) {
        console.error("JSON parse: ", e);
        alert("JSON parse failed");
        return;
      }
      if (!res.ok) {
        console.error("Import failed:", { status: res.status, body });
        const serverMsg =
          body && (body.details || body.error)
            ? body.details
              ? `${body.error}: ${body.details}`
              : body.error
            : `Upload failed with status ${res.status}`;
        alert(`Import failed: ${serverMsg}`);
        return;
      }
      const updated = body || [];
      reloadCalendar(updated);
    } catch (err) {
      console.error("Import failed:", err);
      alert(
        "Could not import file: " +
          (err?.message ? err.message : String(err)),
      );
    } finally {
      importFile.value = "";
    }
  });

  function createDayCell(
    year,
    month,
    day,
    { isOtherMonth = false, allowActions = false } = {},
  ) {
    const cell = document.createElement("div");
    cell.className = "calendar-day" + (isOtherMonth ? " other-month" : "");
    const dateKey = ymd(year, month, day);
    cell.setAttribute("data-date", dateKey);

    const num = document.createElement("div");
    num.className = "day-number";
    num.textContent = day;
    cell.appendChild(num);

    const evWrap = document.createElement("div");
    evWrap.className = "events";

    const evs = eventsFor(dateKey);
    evs.forEach((ev) => {
      const evEl = document.createElement("div");
      evEl.className = "event";

      const titleSpan = document.createElement("span");
      titleSpan.className = "event-title";
      titleSpan.textContent = ev.title;
      evEl.appendChild(titleSpan);

      if (allowActions) {
        const actions = document.createElement("span");
        actions.className = "event-actions";

        const editBtn = document.createElement("button");
        editBtn.className = "edit-btn";
        editBtn.type = "button";
        editBtn.title = "Edit event";
        editBtn.textContent = "✎";
        editBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          const form = inputForm(ev.uid, ev.title, ev.date, ev.end_date || ev.date);
          evEl.innerHTML = "";
          evEl.appendChild(form);
          form.querySelector('input[name="inputTitle"]').focus();
        });

        const delBtn = document.createElement("button");
        delBtn.className = "delete-btn";
        delBtn.type = "button";
        delBtn.title = "Remove event";
        delBtn.textContent = "×";
        delBtn.addEventListener("click", async (e) => {
          e.stopPropagation();
          if (!confirm(`Delete event "${ev.title}" on ${dateKey}?`)) return;
          try {
            const res = await fetch("/event", {
              method: "DELETE",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ uid: ev.uid }),
            });
            if (!res.ok) {
				console.log(res);
				throw new Error("delete failed");
			}
            const updated = await res.json();
            reloadCalendar(updated);
          } catch (err) {
            console.error("Delete event failed", err);
            alert("Could not delete event");
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
      cell.setAttribute(
        "aria-label",
        `${day} ${monthNames[month]} ${year}: ${evs.map((e) => e.title).join(", ")}`,
      );
    }
    // Highlight today's date
    const todayKey = ymd(
      today.getFullYear(),
      today.getMonth(),
      today.getDate(),
    );
    if (dateKey === todayKey) {
      cell.classList.add("today");
    }

    return cell;
  }

  function renderCalendar(year, month) {
    calendarEl.innerHTML = "";
    monthYearEl.textContent = `${monthNames[month]} ${year}`;

    const first = new Date(year, month, 1);
    const startDay = (first.getDay() + 6) % 7; // Start on Monday
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    weekdayNames.forEach((w) => {
      const el = document.createElement("div");
      el.className = "calendar-weekday";
      el.textContent = w;
      calendarEl.appendChild(el);
    });

    // Leading days from previous month
    const prevMonthDate = new Date(year, month, 0);
    const daysInPrevMonth = prevMonthDate.getDate();
    const prevMonthIndex = (month + 11) % 12;
    const prevYear = month === 0 ? year - 1 : year;
    for (let i = startDay; i > 0; i--) {
      const day = daysInPrevMonth - i + 1;
      const cell = createDayCell(prevYear, prevMonthIndex, day, {
        isOtherMonth: true,
        allowActions: false,
      });
      calendarEl.appendChild(cell);
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const cell = createDayCell(year, month, d, {
        isOtherMonth: false,
        allowActions: true,
      });
      calendarEl.appendChild(cell);
    }

    // Trailing days from next month to complete last week
    const used = startDay + daysInMonth;
    const trailing = (7 - (used % 7)) % 7;
    const nextMonthIndex = (month + 1) % 12;
    const nextYear = month === 11 ? year + 1 : year;
    for (let i = 1; i <= trailing; i++) {
      const cell = createDayCell(nextYear, nextMonthIndex, i, {
        isOtherMonth: true,
        allowActions: false,
      });
      calendarEl.appendChild(cell);
    }
  }

  function inputForm(uid, title, dateKey, endDateKey) {
    const form = document.createElement("div");
    form.className = "edit-form";

    const inputTitle = document.createElement("input");
    inputTitle.name = "inputTitle";
    inputTitle.type = "text";
    inputTitle.value = title;
    inputTitle.className = "edit-title";
    inputTitle.addEventListener("click", (ev) => {
      ev.stopPropagation();
    });

    const dateWrap = document.createElement("div");
    dateWrap.className = "edit-date-wrap";
    
    const inputDate = document.createElement("input");
    inputDate.type = "date";
    inputDate.value = dateKey;
    inputDate.className = "edit-date";
    inputDate.addEventListener("click", (ev) => {
      ev.stopPropagation();
    });

    const inputEndDate = document.createElement("input");
    inputEndDate.type = "date";
    inputEndDate.value = endDateKey || dateKey;
    inputEndDate.className = "edit-date end-date";
    inputEndDate.addEventListener("click", (ev) => {
      ev.stopPropagation();
    });

    const toSpan = document.createElement("span");
    toSpan.textContent = " to ";

    dateWrap.appendChild(inputDate);
    dateWrap.appendChild(toSpan);
    dateWrap.appendChild(inputEndDate);

    const saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.className = "save-btn";
    saveBtn.textContent = "Save";
    saveBtn.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      const newTitle = inputTitle.value.trim();
      const newDate = inputDate.value;
      const newEndDate = inputEndDate.value;
      if (!newTitle || !newDate || !newEndDate) {
        alert("Provide a date and a title");
        return;
      }
      if (newEndDate < newDate) {
        alert("End date must be after or equal to start date");
        return;
      }
      try {
        const res = await fetch("/event", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            uid: uid,
            date: newDate,
            end_date: newEndDate,
            title: newTitle,
          }),
        });
        if (!res.ok) throw new Error("save failed");
        const updated = await res.json();
        reloadCalendar(updated);
      } catch (err) {
        console.error("add/update event failed", err);
        alert("Could not add or update an event");
        renderCalendar(currentYear, currentMonth);
      }
    });

    const cancelBtn = document.createElement("button");
    cancelBtn.type = "button";
    cancelBtn.className = "cancel-btn";
    cancelBtn.textContent = "Cancel";
    cancelBtn.addEventListener("click", () => {
      form.remove();
      renderCalendar(currentYear, currentMonth);
    });

    form.appendChild(dateWrap);
    form.appendChild(inputTitle);
    
    const actionsWrap = document.createElement("div");
    actionsWrap.className = "edit-form-actions";
    actionsWrap.appendChild(saveBtn);
    actionsWrap.appendChild(cancelBtn);
    form.appendChild(actionsWrap);

    return form;
  }

  // Add the form when a day is clicked
  calendarEl.addEventListener("click", (e) => {
    // Prevent opening form when clicking action buttons inside event
    if (e.target.closest(".event") || e.target.closest("button") || e.target.closest(".edit-form")) return;

    const dayEl = e.target.closest(".calendar-day");
    if (!dayEl || dayEl.classList.contains("inactive")) return;
    const dateKey = dayEl.getAttribute("data-date");

    // Close open forms
    const existing = document.querySelectorAll(".edit-form");
    existing.forEach((n) => n.remove());

    const form = inputForm(null, "", dateKey, dateKey);
    dayEl.appendChild(form);
    form.querySelector('input[name="inputTitle"]').focus();
  });

  function reloadCalendar(newEvents) {
    if (Array.isArray(newEvents)) {
      window.SERVEREVENTS = newEvents;
    }
    renderCalendar(currentYear, currentMonth);
  }
  prevBtn.addEventListener("click", () => {
    currentMonth -= 1;
    if (currentMonth < 0) {
      currentMonth = 11;
      currentYear -= 1;
    }
    renderCalendar(currentYear, currentMonth);
  });
  nextBtn.addEventListener("click", () => {
    currentMonth += 1;
    if (currentMonth > 11) {
      currentMonth = 0;
      currentYear += 1;
    }
    renderCalendar(currentYear, currentMonth);
  });

  renderCalendar(currentYear, currentMonth);
});
