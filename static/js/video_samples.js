const searchInput = document.getElementById("sample-search-input");
const statusFilter = document.getElementById("sample-status-filter");
const sampleCards = [...document.querySelectorAll(".sample-card")];
const noResults = document.getElementById("sample-no-results");

for (const card of sampleCards) {
  const player = card.querySelector(".sample-player");
  const videoSelect = card.querySelector(".sample-video-select");
  if (!player) continue;

  player.muted = true;
  player.volume = 0;
  player.addEventListener("volumechange", () => {
    if (!player.muted || player.volume !== 0) {
      player.muted = true;
      player.volume = 0;
    }
  });
  if (!videoSelect) continue;

  videoSelect.addEventListener("change", () => {
    player.pause();
    player.src = videoSelect.value;
    player.load();
  });
}

function filterSampleCards() {
  const query = searchInput.value.trim().toLocaleLowerCase("vi");
  const status = statusFilter.value;
  let visibleCount = 0;
  for (const card of sampleCards) {
    const matchesText = card.dataset.search.toLocaleLowerCase("vi").includes(query);
    const matchesStatus = status === "all" || card.dataset.status === status;
    card.hidden = !matchesText || !matchesStatus;
    if (!card.hidden) visibleCount += 1;
  }
  if (noResults) noResults.hidden = visibleCount > 0;
}

searchInput.addEventListener("input", filterSampleCards);
statusFilter.addEventListener("change", filterSampleCards);
filterSampleCards();
