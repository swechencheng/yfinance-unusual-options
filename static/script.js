document.addEventListener("DOMContentLoaded", () => {
  let allData = [];
  let currentSortCol = 'Estimated_Premium';
  let currentSortDir = 'desc'; // 'asc' or 'desc'
  const tbody = document.getElementById("options-tbody");
  const searchInput = document.getElementById("ticker-search");
  const fileSelector = document.getElementById("file-selector");
  const headers = document.querySelectorAll('th.sortable');

  // Format numbers
  const formatCurrency = (num) => {
    if (!num && num !== 0) return "-";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(num);
  };

  const formatNumber = (num, decimals = 2) => {
    if (!num && num !== 0) return "-";
    return Number(num).toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  };

  const getSideClass = (side) => {
    if (!side) return "side-neutral";
    if (side.includes("Buy")) return "side-buy";
    if (side.includes("Sell")) return "side-sell";
    return "side-neutral";
  };

  const getTypeClass = (type) => {
    return type && type.toLowerCase() === "call" ? "type-call" : "type-put";
  };

  const renderTable = (data) => {
    if (data.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="16" style="text-align:center;color:#9ca3af;padding:3rem;">No unusual options data found.</td></tr>';
      return;
    }

    tbody.innerHTML = "";
    data.forEach((row, i) => {
      const tr = document.createElement("tr");
      tr.style.animation = `fadeIn 0.3s ease-out ${i * 0.02}s backwards`;

      const volOiRatio = parseFloat(row["vol/OI"]);
      const ratioClass = volOiRatio > 10 ? "ratio-high" : "";

      tr.innerHTML = `
                <td><span class="ticker-badge">${row.Ticker || "-"}</span></td>
                <td>${row.Expiration || "-"}</td>
                <td class="numerical-value">$${formatNumber(row.strike)}</td>
                <td class="numerical-value">$${formatNumber(row.Stock_Price)}</td>
                <td><span class="type-badge ${getTypeClass(row.Type)}">${row.Type || "-"}</span></td>
                <td><span class="side-badge ${getSideClass(row.Estimated_Side)}">${row.Estimated_Side || "-"}</span></td>
                <td class="premium-value">${formatCurrency(row.Estimated_Premium)}</td>
                <td class="numerical-value ${ratioClass}">${formatNumber(volOiRatio, 1)}x</td>
                <td class="numerical-value" style="color:${row.Moneyness > 0 ? '#10b981' : (row.Moneyness < 0 ? '#ef4444' : '#9ca3af')};">${row.Moneyness > 0 ? '+' : ''}${formatNumber(row.Moneyness, 1)}%</td>
                <td class="numerical-value">${formatNumber(row.lastPrice, 2)}</td>
                <td class="numerical-value" style="color:#9ca3af;">${formatNumber(row.bid, 2)}</td>
                <td class="numerical-value" style="color:#9ca3af;">${formatNumber(row.ask, 2)}</td>
                <td class="numerical-value">${formatNumber(row.volume, 0)}</td>
                <td class="numerical-value">${formatNumber(row.openInterest, 0)}</td>
                <td class="numerical-value">${formatNumber(row.impliedVolatility * 100, 1)}%</td>
                <td style="white-space:nowrap;color:#9ca3af;font-size:0.85rem;">${row.Updated ? row.Updated.split(" ")[1] || row.Updated : "-"}</td>
            `;
      tbody.appendChild(tr);
    });
  };

  // Sorting logic
  const sortData = (data, col, dir) => {
    return [...data].sort((a, b) => {
      let valA = a[col];
      let valB = b[col];

      // Handle undefined/null
      if (valA === undefined || valA === null) valA = '';
      if (valB === undefined || valB === null) valB = '';

      // Numerical sorting
      const numA = Number(valA);
      const numB = Number(valB);

      if (!isNaN(numA) && !isNaN(numB) && valA !== '' && valB !== '') {
        return dir === 'asc' ? numA - numB : numB - numA;
      }

      // String sorting
      const strA = String(valA).toLowerCase();
      const strB = String(valB).toLowerCase();

      if (strA < strB) return dir === 'asc' ? -1 : 1;
      if (strA > strB) return dir === 'asc' ? 1 : -1;
      return 0;
    });
  };

  const updateTable = () => {
    const term = searchInput.value.toLowerCase();
    let displayData = allData;

    if (term) {
      displayData = allData.filter(row =>
        (row.Ticker && row.Ticker.toLowerCase().includes(term))
      );
    }

    displayData = sortData(displayData, currentSortCol, currentSortDir);
    renderTable(displayData);
  };

  // Header click listeners
  headers.forEach(th => {
    th.addEventListener('click', () => {
      const col = th.getAttribute('data-sort');
      if (currentSortCol === col) {
        // Toggle direction
        currentSortDir = currentSortDir === 'asc' ? 'desc' : 'asc';
      } else {
        // New column, default to desc
        currentSortCol = col;
        currentSortDir = 'desc';
      }

      // Update icons
      headers.forEach(h => {
        h.classList.remove('sort-asc', 'sort-desc');
        const sortIcon = h.querySelector('.sort-icon');
        if (sortIcon) sortIcon.textContent = '';
      });
      th.classList.add(`sort-${currentSortDir}`);
      const currentSortIcon = th.querySelector('.sort-icon');
      if (currentSortIcon) currentSortIcon.textContent = currentSortDir === 'asc' ? '▲' : '▼';

      updateTable();
    });
  });

  const loadData = (filename = null) => {
    let url = "/api/options";
    if (filename) {
      url += `?filename=${encodeURIComponent(filename)}`;
    }

    tbody.innerHTML = '<tr><td colspan="16" class="loading-cell"><div class="loader"></div>Loading data...</td></tr>';

    fetch(url)
      .then((res) => res.json())
      .then((result) => {
        if (result.error) {
          tbody.innerHTML = `<tr><td colspan="16" style="text-align:center;color:#f87171;padding:3rem;">Error: ${result.error}</td></tr>`;
          return;
        }

        allData = result.data || [];

        // Extract filename from full path, then extract date part
        const filePath = result.date || "";
        const fileName = filePath.split("/").pop();
        const dateMatch = fileName.match(/\d{4}-\d{2}-\d{2}/);
        const dateStr = dateMatch ? dateMatch[0] : "Unknown";

        document.getElementById("file-loaded-stat").textContent = dateStr;
        document.getElementById('total-sweeps-stat').textContent = allData.length.toLocaleString();

        updateTable();
      })
      .catch(err => {
        tbody.innerHTML = `<tr><td colspan="16" style="text-align:center;color:#f87171;padding:3rem;">Failed to fetch data: ${err}</td></tr>`;
      });
  };

  // Fetch available files and populate dropdown
  fetch("/api/options/files")
    .then(res => res.json())
    .then(result => {
      if (result.files && result.files.length > 0) {
        fileSelector.innerHTML = '';
        result.files.forEach(file => {
          const option = document.createElement('option');
          option.value = file;
          // extract formatting for display
          const dateMatch = file.match(/\d{4}-\d{2}-\d{2}/);
          const displayDate = dateMatch ? dateMatch[0] : file;

          let label = "Options";
          if (file.includes('_us_')) label = "US Market";
          if (file.includes('_omxs30_')) label = "OMXS30";

          option.textContent = `${label} (${displayDate})`;
          fileSelector.appendChild(option);
        });

        // Load the first (latest) file by default
        loadData(result.files[0]);
      } else {
        fileSelector.innerHTML = '<option value="">No files found</option>';
        loadData(); // Fallback
      }
    })
    .catch(err => {
      console.error("Error fetching files:", err);
      loadData(); // Fallback
    });

  fileSelector.addEventListener('change', (e) => {
    const selectedFile = e.target.value;
    if (selectedFile) {
      loadData(selectedFile);
    }
  });

  // Search filter
  searchInput.addEventListener('input', updateTable);
});
