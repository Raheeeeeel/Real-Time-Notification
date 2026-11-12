const reminderForm = document.querySelector("#reminderForm");
const titleInput = document.querySelector("#title");
const timeInput = document.querySelector("#remind_time");
const searchInput = document.querySelector("#reminderSearch");
const filterButtons = document.querySelectorAll(".filter-tab");
const reminderItems = [...document.querySelectorAll(".reminder-item")];
const emptyState = document.querySelector("#emptyState");
const noResults = document.querySelector("#noResults");
let activeFilter = "all";

function localDateTimeValue(date) {
    const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return localDate.toISOString().slice(0, 16);
}

if (timeInput) {
    timeInput.min = localDateTimeValue(new Date());
}

if (titleInput) {
    titleInput.addEventListener("input", () => titleInput.setCustomValidity(""));
}

if (reminderForm) {
    reminderForm.addEventListener("submit", (event) => {
        if (!titleInput.value.trim()) {
            event.preventDefault();
            titleInput.setCustomValidity("Please enter a reminder title.");
            titleInput.reportValidity();
            titleInput.focus();
            return;
        }

        titleInput.value = titleInput.value.trim();
        const submitButton = reminderForm.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.innerHTML = "<span aria-hidden=\"true\">…</span> Saving reminder";
    });
}

function updateReminderList() {
    const query = searchInput?.value.trim().toLocaleLowerCase() ?? "";
    let visibleCount = 0;

    reminderItems.forEach((item) => {
        const matchesFilter = activeFilter === "all" || item.dataset.status === activeFilter;
        const matchesSearch = item.dataset.search.includes(query);
        const visible = matchesFilter && matchesSearch;
        item.hidden = !visible;
        if (visible) visibleCount += 1;
    });

    if (emptyState) {
        emptyState.hidden = reminderItems.length > 0;
    }
    if (noResults) {
        noResults.hidden = reminderItems.length === 0 || visibleCount > 0;
    }
}

if (searchInput) {
    searchInput.addEventListener("input", updateReminderList);
}

filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
        activeFilter = button.dataset.filter;
        filterButtons.forEach((tab) => {
            const selected = tab === button;
            tab.classList.toggle("active", selected);
            tab.setAttribute("aria-pressed", String(selected));
        });
        updateReminderList();
    });
});

document.querySelectorAll(".delete-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
        const reminderTitle = form.closest(".reminder-item")
            ?.querySelector("h3")?.textContent.trim() || "this reminder";
        if (!window.confirm(`Delete "${reminderTitle}"? This can't be undone.`)) {
            event.preventDefault();
        }
    });
});

document.querySelectorAll(".reminder-item.pending").forEach((item) => {
    const timeLabel = item.querySelector(".relative-time");
    if (!timeLabel) return;

    const remindTime = new Date(item.dataset.remindTime);
    const difference = remindTime.getTime() - Date.now();

    if (Number.isNaN(difference)) return;
    if (difference < 0) {
        timeLabel.textContent = "Overdue";
        timeLabel.classList.add("overdue");
    } else if (difference < 60 * 60 * 1000) {
        const minutes = Math.max(1, Math.ceil(difference / 60000));
        timeLabel.textContent = `In ${minutes} min`;
    } else if (difference < 24 * 60 * 60 * 1000) {
        const hours = Math.ceil(difference / (60 * 60 * 1000));
        timeLabel.textContent = `In ${hours} ${hours === 1 ? "hour" : "hours"}`;
    } else {
        const days = Math.ceil(difference / (24 * 60 * 60 * 1000));
        timeLabel.textContent = `In ${days} ${days === 1 ? "day" : "days"}`;
    }
});

const todayLabel = document.querySelector("#todayLabel");
if (todayLabel) {
    todayLabel.textContent = new Intl.DateTimeFormat(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
    }).format(new Date());
}

updateReminderList();
