const SESSION_TIME =
    7 * 24 * 60 * 60 * 1000;;
let SHOP_PROFILE = null;
let cart = [];
let currentGrandTotal = 0;
let currentFilter = "all";
let editingId = null;
let invoiceCounter = parseInt(
    localStorage.getItem("invoiceCounter")
) || 1;


async function api(url, opts) {
    const shopId =
    localStorage.getItem(
        "shop_id"
    );

if (
    !shopId &&
    !url.includes("/login")
) {

    alert(
        "Please login first"
    );

    location.reload();

    return;
}
    const res = await fetch(url, opts);

    try {
        return await res.json();
    } catch {
        return {};
    }
}

// Theme
function loadTheme() {

    const isDark =
        localStorage.getItem("theme") === "dark";

    document.documentElement.setAttribute(
        "data-theme",
        isDark ? "dark" : "light"
    );

    const btn =
        document.getElementById("themeBtn");

    if (btn) {

        btn.innerHTML =
            isDark ? "☀️" : "🌙";
    }
}

// Navigation
function navigate(view) {
    const shopId =
    localStorage.getItem(
        "shop_id"
    );

if (!shopId) {

    alert(
        "Please login first"
    );

    return;
}
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
    document.getElementById("view-" + view).classList.add("active");
    document.querySelector(`[data-view="${view}"]`).classList.add("active");
    if (view === "dashboard") {

    loadDashboard();

    loadAnalytics();
}
    
if(view === "customers"){

    loadCustomers();

    loadCustomerAnalytics();
}
    if (view === "inventory") loadMedicines();
    if (view === "billing") searchForBilling();
    if (view === "wholesalers") loadWholesalers();
    if (view === "bills") loadBills();
    if (view === "orders") loadOrders();
    if (view === "settings") loadSettings();
    closeSidebar();
}

function toggleSidebar() {
    document.getElementById("sidebar").classList.toggle("open");
    document.getElementById("sidebarOverlay").classList.toggle("show");
}

function closeSidebar() {
    document.getElementById("sidebar").classList.remove("open");
    document.getElementById("sidebarOverlay").classList.remove("show");
}
function toggleCollapse() {

    const sidebar =
        document.getElementById(
            "sidebar"
        );

    if (!sidebar) return;

    sidebar.classList.toggle(
        "collapsed"
    );

    localStorage.setItem(
        "sidebarCollapsed",
        sidebar.classList.contains(
            "collapsed"
        )
    );
}
window.addEventListener(
    "load",
    () => {

        if (
            localStorage.getItem(
                "sidebarCollapsed"
            ) === "true"
        ) {

            document
                .getElementById("sidebar")
                .classList
                .add("collapsed");
        }
    }
);

function getStatus(med) {

    if (med.quantity === 0) {
        return {
            text: "Out of Stock",
            cls: "badge-danger",
            row: "row-out"
        };
    }

    if (med.quantity <= 10) {
        return {
            text: "Low Stock",
            cls: "badge-warning",
            row: "row-low"
        };
    }

    return {
        text: "In Stock",
        cls: "badge-success",
        row: ""
    };
}

function formatDate(d) {
    if (!d) return "-";
    return new Date(d).toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
}

function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}

// Dashboard
async function loadDashboard() {
    console.log("loadDashboard running...");
    function animateNumber(id, value) {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = value;
    }

    const data = await api(
        `/api/dashboard?shop_id=${localStorage.getItem("shop_id")}`
    );
    SHOP_PROFILE = data;

    console.log(JSON.stringify(data, null, 2));

    animateNumber(
        "stat-total",
        data.total || 0
    );

    animateNumber(
        "stat-low",
        data.low_stock || 0
    );

    animateNumber(
        "stat-out",
        data.out_of_stock || 0
    );

    document.getElementById(
        "today-sales"
    ).textContent =
        "₹" + (data.today_sales || 0);

    document.getElementById(
        "today-bills"
    ).textContent =
        data.today_bills || 0;

    document.getElementById(
        "monthly-revenue"
    ).textContent =
        "₹" + (data.monthly_revenue || 0);
    document.getElementById(
    "average-bill"
).textContent =
    "₹" + (data.average_bill || 0);

document.getElementById(
    "highest-bill"
).textContent =
    "₹" + (data.highest_bill || 0);

const bestDayEl =
document.getElementById(
    "best-sales-day"
);

if(bestDayEl){

    bestDayEl.textContent =
    data.best_sales_day || "-";

}

const amountEl =
document.getElementById(
    "best-sales-amount"
);

if(amountEl){

    amountEl.textContent =
    "₹" +
    (
        data.best_sales_amount || 0
    );

}

document.getElementById(
    "collection-rate"
).textContent =
    (data.collection_rate || 0)
    + "%"; 
    
    const growthElement =
document.getElementById(
    "revenue-growth"
);

if (growthElement) {

    if (
        data.revenue_growth === null
    ) {

        growthElement.textContent =
            "N/A";

    } else {

        growthElement.textContent =
            data.revenue_growth + "%";
    }
}
    
    document.getElementById(
    "stat-sales-items"
    ).textContent =
    data.total_sales_items || 0;    

    const items = await api(
        `/api/low-stock?shop_id=${localStorage.getItem("shop_id")}`
    );

    const el =
        document.getElementById(
            "alert-list"
        );

   if (!items.length) {

    el.innerHTML =
        `
        <div class="empty-state">
            <p>
                All stock levels are healthy
            </p>
        </div>
        `;
}
else {

// STOCK ALERTS

let stockHtml = "";

stockHtml += items.map(m => {

    const badge =
        m.quantity === 0
            ? `
            <span class="badge badge-danger">
                Out of Stock
            </span>
            `
            : `
            <span class="badge badge-warning">
                Qty: ${m.quantity}
            </span>
            `;

    return `
    <div class="alert-row">

        <span class="alert-name">
            ${escapeHtml(m.name)}
        </span>

        ${badge}

    </div>
    `;
}).join("");

el.innerHTML = stockHtml;
}
// EXPIRY ALERTS

let expiryHtml = "";

const medicines = await api(
    `/api/medicines?shop_id=${localStorage.getItem("shop_id")}`
);

medicines.forEach(med => {

    if (
        med.expiry_status ===
        "expired"
    ) {

        expiryHtml += `
        <div class="alert-row">

            <span class="alert-name">
                🔴 ${escapeHtml(med.name)}
            </span>

            <span class="badge badge-danger">
                Expired
                ${Math.abs(
                    med.days_left
                )} days ago
            </span>

        </div>
        `;
    }

    else if (
        med.expiry_status ===
        "warning"
    ) {

        expiryHtml += `
        <div class="alert-row">

            <span class="alert-name">
                🟡 ${escapeHtml(med.name)}
            </span>

            <span class="badge badge-warning">
                ${med.days_left}
                days left
            </span>

        </div>
        `;
    }
});

const expiryEl =
    document.getElementById(
        "expiry-alert-list"
    );

if (expiryEl) {
    expiryEl.innerHTML =
        expiryHtml;
}


}

// Inventory
function setFilter(f) {
    currentFilter = f;
    document.querySelectorAll(".pill").forEach(b => b.classList.toggle("active", b.dataset.filter === f));
    loadMedicines();
}

async function loadMedicines() {
    const search =
    document.getElementById(
        "search-input"
    )?.value || "";
   const meds = await api(
    `/api/medicines?shop_id=${localStorage.getItem("shop_id")}&search=${encodeURIComponent(search)}&filter=${currentFilter}`
);
    const tbody = document.getElementById("medicine-tbody");
    const empty = document.getElementById("medicine-empty");
    const table = document.getElementById("medicine-table");

    if (!meds.length) {
        table.style.display = "none";
        empty.style.display = "block";
        return;
    }
    table.style.display = "";
    empty.style.display = "none";

    tbody.innerHTML = meds.map(m => {
       const s = getStatus(m);

let expiryBadge = "";

if (m.status?.expiry === "expired") {
    expiryBadge = `
        <span class="badge badge-danger">
            Expired
        </span>
    `;
}
else {
    expiryBadge = "";
}
        return `<tr class="${s.row}">
            <td class="med-name-cell">${escapeHtml(m.name)}</td>
            <td>${escapeHtml(m.category) || '<span style="color:var(--text-tertiary)">-</span>'}</td>
            <td><strong>${m.quantity}</strong></td>
            <td class="med-price">₹${m.price.toFixed(2)}</td>
           <td>
    <div>
        ${formatDate(m.expiry_date)}
        <br>
        ${expiryBadge}
    </div>
</td>
            <td>${m.gst || 0}%</td>
            <td><span class="badge ${s.cls}">${s.text}</span></td>
            <td><div class="td-actions">
                <button class="icon-btn edit-btn" onclick="openEditModal(${m.id})">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button class="icon-btn danger" onclick="deleteMedicine(${m.id})" title="Delete">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                </button>
            </div></td>
        </tr>`;
    }).join("");
}

function openMedicineModal() {
    editingId = null;
    document.getElementById("medicine-modal-title").textContent = "Add Medicine";
    document.getElementById("medicine-form").reset();
    document.getElementById("medicine-modal").classList.add("active");
}

async function openEditModal(id) {
    const meds = await api(
    `/api/medicines?shop_id=${localStorage.getItem("shop_id")}`
);
    const m = meds.find(x => x.id === id);
    if (!m) return;
    editingId = id;
    document.getElementById("medicine-modal-title").textContent = "Edit Medicine";
    document.getElementById("med-name").value = m.name;
    document.getElementById("med-qty").value = m.quantity;
    document.getElementById("med-price").value = m.price;
    document.getElementById("med-category").value = m.category;
    document.getElementById("med-expiry").value = m.expiry_date;
    document.getElementById("medicine-modal").classList.add("active");
    document.getElementById("med-gst").value = m.gst || 0;
}

function closeMedicineModal() {
    document.getElementById("medicine-modal").classList.remove("active");
}

async function saveMedicine(e) {
    e.preventDefault();
    const data = {

    name:
        document.getElementById(
            "med-name"
        ).value.trim(),

    quantity:
        parseInt(
            document.getElementById(
                "med-qty"
            ).value
        ),

    price:
        parseFloat(
            document.getElementById(
                "med-price"
            ).value
        ),

    category:
        document.getElementById(
            "med-category"
        ).value,

    expiry_date:
        document.getElementById(
            "med-expiry"
        ).value,

    gst:
        parseFloat(
            document.getElementById(
                "med-gst"
            ).value
        ) || 0,

    // 🔥 IMPORTANT

    shop_id:
        localStorage.getItem(
            "shop_id"
        )
};
    const opts = { method: editingId ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) };
    const url = editingId ? `/api/medicines/${editingId}` : "/api/medicines";

    await api(url, opts);

    closeMedicineModal();
    loadMedicines();
    loadDashboard(); // ✅ ADD THIS
}

async function deleteMedicine(id) {
    if (!confirm("Delete this medicine?")) return;

    await api(`/api/medicines/${id}`, { method: "DELETE" });

    loadMedicines();
    loadDashboard(); // ✅ ADD THIS
}

// Billing
async function searchForBilling() {

    const search =
        document.getElementById(
            "billing-search"
        ).value;

    const shopId =
        localStorage.getItem(
            "shop_id"
        );

    const meds = await api(
        `/api/medicines?shop_id=${shopId}&search=${encodeURIComponent(search)}`
    );
    const el = document.getElementById("billing-results");
    const available = meds.filter(m => m.quantity > 0);
    if (!available.length) {
        el.innerHTML = '<div class="empty-state"><p>No products available</p></div>';
        return;
    }
    el.innerHTML = available.map(m => `<div class="pos-product">
        <div class="pos-prod-info">
            <div class="pos-prod-name">${escapeHtml(m.name)}</div>
            <div class="pos-prod-meta">${escapeHtml(m.category) || "General"} &middot; Stock: ${m.quantity}</div>
        </div>
        <div class="pos-prod-price">₹${m.price.toFixed(2)}</div>
        <button class="pos-add-btn" onclick='addToCart(${JSON.stringify(m)})' title="Add to cart">+</button>
    </div>`).join("");
}

function addToCart(med) {
    const existing = cart.find(c => c.id === med.id);
    if (existing) {
    if (existing.qty < med.quantity) {
        existing.qty++;
        existing.gst = med.gst || 0; // ✅ ADD THIS
    }
} else {
        cart.push({ id: med.id, name: med.name, price: med.price, qty: 1, maxQty: med.quantity,gst: med.gst || 0 });
    }
    renderCart();
}

function updateQty(idx, delta) {
    cart[idx].qty += delta;
    if (cart[idx].qty <= 0) cart.splice(idx, 1);
    else if (cart[idx].qty > cart[idx].maxQty) cart[idx].qty = cart[idx].maxQty;
    renderCart();
}

function removeFromCart(idx) {
    cart.splice(idx, 1);
    renderCart();
}

function renderCart() {
    const el = document.getElementById("cart-items");
    const countEl = document.getElementById("cart-count");
    if (!cart.length) {
        el.innerHTML = '<div class="empty-state"><p>No items in cart</p></div>';
        document.getElementById("cart-total").textContent = "₹0.00";
        countEl.textContent = "0 items";
        return;
    }
    let total = 0;


    el.innerHTML = cart.map((c, i) => {
        const sub = c.price * c.qty;
const gstAmount =
    SHOP_PROFILE &&
    SHOP_PROFILE.business_type ===
    "GST Registered"
        ? sub * (c.gst || 0) / 100
        : 0;
total += sub + gstAmount; 
        return `<div class="cart-row">
           <div class="cart-item-info">
    <div class="cart-item-name">${escapeHtml(c.name)}</div>
    <div class="cart-item-price">
        ₹${c.price.toFixed(2)} + ${c.gst || 0}% GST
    </div>
            </div>
            <div class="qty-control">
                <button class="qty-btn" onclick="updateQty(${i},-1)">&minus;</button>
                <span class="qty-val">${c.qty}</span>
                <button class="qty-btn" onclick="updateQty(${i},1)">+</button>
            </div>
            <div class="cart-line-total">
    ₹${(sub + gstAmount).toFixed(2)}
</div>
            <button class="cart-remove" onclick="removeFromCart(${i})" title="Remove">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
        </div>`;
    }).join("");
    document.getElementById("cart-total").textContent = `₹${total.toFixed(2)}`;
    countEl.textContent = `${cart.reduce((a, c) => a + c.qty, 0)} items`;
}
updateDueAmount();

function clearCart() {
    cart = [];
    renderCart();
}

function updateDueAmount(){

    const paid =
        parseFloat(
            document.getElementById(
                "paidAmount"
            )?.value
        ) || 0;

    const total =
        parseFloat(
            document.getElementById(
                "cart-total"
            ).innerText.replace(
                "₹",
                ""
            )
        ) || 0;

    const due =
        Math.max(
            total - paid,
            0
        );

    document.getElementById(
        "remainingDue"
    ).innerText =
        `₹${due.toFixed(2)}`;
}

async function generateBill() {
    const customerName = document.getElementById("customer-name")?.value || "Walk-in Customer";
    const customerPhone =
    document.getElementById("customer-phone")?.value.trim() || "";
    document.getElementById("customer-phone").value = "";
    const invoiceNo = "INV-" + String(invoiceCounter).padStart(3, "0");
    if (!cart.length) return alert("Cart is empty");
const now = new Date();
const isGSTShop =
    SHOP_PROFILE &&
    SHOP_PROFILE.business_type ===
    "GST Registered";
   let subtotal = 0;
let totalGST = 0;
const rows = cart.map(c => {
    const sub = c.price * c.qty;
const gstAmount =
    isGSTShop
        ? sub * (c.gst || 0) / 100
        : 0;


    subtotal += sub;
    totalGST += gstAmount;

    return `<tr>
        <td>${escapeHtml(c.name)}</td>
        <td>${c.qty}</td>
        <td>₹${c.price.toFixed(2)}</td>
        ${
    isGSTShop
    ? `
        <td>${c.gst || 0}%</td>
        <td>₹${gstAmount.toFixed(2)}</td>
      `
    : ""
}
        <td>₹${(sub + gstAmount).toFixed(2)}</td>
    </tr>`;
}).join("");

const grandTotal = subtotal + totalGST;
currentGrandTotal = grandTotal;

const finalPaid =
    document.getElementById(
        "paidAmount"
    ).value === ""

    ? grandTotal

    : parseFloat(
        document.getElementById(
            "paidAmount"
        ).value
    );

if (finalPaid < 0) {

    alert(
        "Paid amount cannot be negative"
    );

    return;
}

const finalDue =
    Math.max(
        grandTotal - finalPaid,
        0
    );

    document.getElementById("bill-content").innerHTML = `
<div class="bill">
       <div class="bill-header">

    <div class="invoice-brand">

        ${
    localStorage.getItem("shop_logo")

    ? `

    <img
        src="${
            localStorage.getItem("shop_logo")
        }"
        class="invoice-logo"
    >

    `

    : `

    <div class="invoice-logo-placeholder">

        ${
            (
                SHOP_PROFILE?.shop_name
                || "M"
            )[0]
        }

    </div>
    `
}

        <h2>
            ${
                SHOP_PROFILE?.shop_name
                || "Medical Shop"
            }
        </h2>

        <span class="invoice-tagline">
            Trusted Pharma Network
        </span>

    </div>
    

    <div class="invoice-meta-grid">

        <div class="invoice-meta-item">
            👤 Owner:
            ${
                SHOP_PROFILE?.owner_name
                || "-"
            }
        </div>

        <div class="invoice-meta-item">
            🧾 Customer:
            ${customerName}
        </div>

        <div class="invoice-meta-item">
            📞 Phone:
            ${customerPhone}
        </div>

    </div>

    <div class="invoice-meta-bar">

        <span>
            Invoice:
            ${invoiceNo}
        </span>

        <span>
            ${
                now.toLocaleDateString(
                    "en-IN",
                    {
                        weekday: "short",
                        year: "numeric",
                        month: "short",
                        day: "numeric"
                    }
                )
            }
        </span>

        <span>
            ${
                now.toLocaleTimeString(
                    "en-IN",
                    {
                        hour: "2-digit",
                        minute: "2-digit"
                    }
                )
            }
        </span>

    </div>

</div>
        <table class="bill-table">
            <thead>
<tr>
<th>Item</th>
<th>Qty</th>
<th>Price</th>
${
    isGSTShop
    ? `
        <th>GST %</th>
        <th>GST</th>
      `
    : ""
}
<th>Total</th>
</tr>
</thead>
            <tbody>${rows}</tbody>
        </table>

    ${
        isGSTShop
        ? `
        <div class="summary-row">
            <span>GST</span>
            <strong>
                ₹${totalGST.toFixed(2)}
            </strong>
        </div>
        `
        : ""
    }

    <div class="summary-divider"></div>

    <div class="summary-grand">

        <span>
            Grand Total
        </span>

        <strong>
            ₹${grandTotal.toFixed(2)}
        </strong>

    </div>
    <div class="summary-row">
    <span>Paid Amount</span>
    <strong>₹${finalPaid.toFixed(2)}</strong>
</div>

<div class="summary-row">
    <span>Due Amount</span>
    <strong class="${
        finalDue > 0
        ? "payment-due"
        : "payment-paid"
    }">
        ₹${finalDue.toFixed(2)}
    </strong>
</div>

<div class="summary-row">
    <span>Payment Method</span>
    <strong>${
        document.getElementById(
            "paymentMethod"
        ).value
    }</strong>
</div>

<div class="summary-row">
    <span>Status</span>
    <strong class="${
        finalDue > 0
        ? "payment-due"
        : "payment-paid"
    }">
        ${
            finalDue > 0
            ? "Due"
            : "Paid"
        }
    </strong>
</div>
    ${generateUPIQR(grandTotal)}

<div class="signature-block">

    Authorized Signature

</div>

<div class="bill-footer">

    <p>
        Goods once sold will not be taken back.
    </p>

    <p>
        Subject to local jurisdiction only.
    </p>

    <p>
        Please keep this invoice for warranty & return purposes.
    </p>

    <p>
        Powered by MedicoSaathi 
    </p>

</div>

<div class="bill-footer">Thank you! Visit Again 🙏</div>

</div>
</div>`;

    document.getElementById("bill-modal").classList.add("active");

    // 🔥 STOCK UPDATE (IMPORTANT)
    const res = await api("/api/sell", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cart)
});

console.log(res);
if (res.error) {

    alert(res.error);

    return;
}

    // 🔄 RESET + REFRESH
const billItems = cart.map(i => ({
    name: i.name,
    qty: i.qty,
    price: i.price,
    gst: i.gst || 0
}));

const saveRes = await api("/api/save-bill", {

    method: "POST",

    headers: {
        "Content-Type": "application/json"
    },

    body: JSON.stringify({
    invoice: invoiceNo,
    name: customerName,
    phone: customerPhone,
    total: grandTotal,
    date: new Date().toISOString(),
    items: billItems,

    shop_id:
        localStorage.getItem(
            "shop_id"
        ),

    paid_amount: finalPaid,

    due_amount: finalDue,

    payment_method:
        document.getElementById(
            "paymentMethod"
        ).value,

    payment_status:
        finalDue > 0
            ? "Due"
            : "Paid"
})
});

if (saveRes.error) {

    alert(saveRes.error);

    return;
}

document.getElementById(
    "customer-name"
).value = "";

document.getElementById(
    "customer-phone"
).value = "";

cart = [];
renderCart();

await loadDashboard();

await loadMedicines();

await loadBills();

await loadCustomers();

invoiceCounter++;

localStorage.setItem(
    "invoiceCounter",
    invoiceCounter
);

// RESET PAYMENT SECTION

document.getElementById(
    "paidAmount"
).value = "";

document.getElementById(
    "paymentMethod"
).value = "Cash";

document.getElementById(
    "remainingDue"
).innerText = "₹0.00";

}

function printBill() {
    window.print();
}
function generateUPIQR(
    amount
) {

    const upi =
        SHOP_PROFILE?.upi_id;

    if (!upi) return "";

    const shopName =
        SHOP_PROFILE?.shop_name
        || "Medical Shop";

    const upiURL =
        `https://upi://pay?pa=${upi}&pn=${shopName}&am=${amount}&cu=INR`;

    return `
        <div class="upi-section">

            <img
                src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(upiURL)}"
                class="upi-qr"
            >

        </div>
    `;
}
function resetInvoice() {
    if (!confirm("Reset invoice number to 1?")) return;
    invoiceCounter = 1;
    localStorage.setItem("invoiceCounter", invoiceCounter);
    alert("Invoice reset to INV-001");
}
function setInvoiceNumber() {
    let num = prompt("Enter invoice number (e.g. 25):");
    if (!num) return;

    invoiceCounter = parseInt(num);
    localStorage.setItem("invoiceCounter", invoiceCounter);

    alert("Invoice set to INV-" + String(invoiceCounter).padStart(3, "0"));
}
// Wholesalers
async function loadWholesalers() {
    const list = await api("/api/wholesalers");
    const el = document.getElementById("wholesaler-list");
    if (!list.length) {
        el.innerHTML = '<div class="empty-state"><p>No wholesalers added</p></div>';
        return;
    }
    el.innerHTML = list.map(w => {
        const initials = w.name.split(" ").map(w => w[0]).join("").substring(0, 2).toUpperCase();
        return `<div class="ws-card">
            <div class="ws-top">
                <div class="ws-info">
                    <div class="ws-avatar">${initials}</div>
                    <div>
                        <div class="ws-name">${escapeHtml(w.name)}</div>
                        <div class="ws-phone">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>
                            ${escapeHtml(w.phone)}
                        </div>
                    </div>
                </div>
                <button class="icon-btn danger" onclick="deleteWholesaler(${w.id})" title="Delete">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                </button>
            </div>
            <div class="ws-btns">
                <a href="tel:${escapeHtml(w.phone)}" class="btn-call">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>
                    Call
                </a>
                <button class="btn-whatsapp" onclick='whatsappWholesaler(${JSON.stringify(w.phone)}, ${JSON.stringify(w.name)})'>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                    WhatsApp
                </button>
            </div>
        </div>`;
    }).join("");
}

function openWholesalerModal() {
    document.getElementById("wholesaler-modal").classList.add("active");
}

function closeWholesalerModal() {
    document.getElementById("wholesaler-modal").classList.remove("active");
}

async function saveWholesaler(e) {
    e.preventDefault();
    await api("/api/wholesalers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: document.getElementById("ws-name").value.trim(),
            phone: document.getElementById("ws-phone").value.trim()
        })
    });
    closeWholesalerModal();
    e.target.reset();
    loadWholesalers();
}

async function deleteWholesaler(id) {
    if (!confirm("Delete this wholesaler?")) return;
    await api(`/api/wholesalers/${id}`, { method: "DELETE" });
    loadWholesalers();
}

async function whatsappWholesaler(phone, name) {
    try {
        const all = await api(
    `/api/medicines?shop_id=${localStorage.getItem("shop_id")}`
);

        const items = all.filter(m => m.quantity === 0);

        if (!items.length) {
            alert("No low or out stock items");
            return;
        }

        let msg = "Out of Stock Sita Sewa Sadan:\n\n";
        msg += items.map(m => `- ${m.name} (Qty: ${m.quantity})`).join("\n");

        const clean = phone.replace(/\D/g, "");

        // ✅ WhatsApp open
// ✅ WhatsApp open
// ✅ WhatsApp open
window.open(
    `https://wa.me/${clean}?text=${encodeURIComponent(msg)}`,
    "_blank"
);

// ✅ Wait until user returns to app
let alreadyHandled = false;

window.onfocus = async function () {

    if (alreadyHandled) return;

    alreadyHandled = true;

    const sent = confirm(
        "Did you send the WhatsApp order?"
    );

    // ✅ User cancelled
    if (!sent) {

        window.onfocus = null;

        return;
    }

    // 🔥 SAVE ORDER
    const res = await fetch("/api/order-stock", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            items: items.map(i => ({
                name: i.name,
                qty: 0
            })),
            wholesaler: name
        })
    });

    const data = await res.json();

    console.log("ORDER SAVE RESPONSE:", data);

    if (data.status === "ok") {

        alert("Order History Saved ✅");

        loadOrders();

    } else {

        alert("Save failed ❌");
    }

    // ✅ cleanup
    window.onfocus = null;
};
    } catch (err) {
        console.error("FULL ERROR:", err);
        alert("Error aa raha hai console check karo");
    }
}

async function loadBills() {
    const data = await api(
    `/api/bills?shop_id=${localStorage.getItem("shop_id")}`
);
    const tbody = document.getElementById("bill-tbody");

    if (!data.length) {
        tbody.innerHTML = "<tr><td colspan='6'>No Bills Found</td></tr>";
        return;
    }

    tbody.innerHTML = data.map(b => {

    let items = [];

    try {
        items = JSON.parse(b.items || "[]");
    } catch {
        items = [];
    }

    return `
    <tr>
        <td>${b.invoice}</td>
        <td>${b.customer_name}</td>
        <td>${b.phone}</td>
        <td>₹${b.total}</td>
        <td>${new Date(b.date).toLocaleDateString()}</td>

        <td>
            <button class="btn btn-danger-ghost btn-sm"
                onclick="deleteBill(${b.id})">
                Delete
            </button>
        </td>
    </tr>

    <tr class="bill-items-row">
        <td colspan="100%">

            ${items.map(i => `
                <div class="bill-med-row">
                    ${i.name} — Qty: ${i.qty}
                </div>
            `).join("")}

        </td>
    </tr>
    `;
}).join("");
}
async function loadOrders() {
    const data = await api("/api/orders");
    const el = document.getElementById("order-list");

    if (!data.length) {
        el.innerHTML = `<div class="empty-state">No orders found</div>`;
        return;
    }

    el.className = "order-cards";

    el.innerHTML = data.map(o => `
        <div class="order-card">

            <div class="order-header">
                <div class="ws-title">

    <div class="ws-avatar">
        <svg width="18" height="18" viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round">

            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"/>

        </svg>
    </div>

    <div>
        <strong>${o.wholesaler}</strong>

        <span class="order-date">
            ${formatDate(o.date)}
        </span>
    </div>

</div>

                <button 
                    class="delete-btn"
                    onclick="deleteOrder('${o.order_id}')">
                    Delete
                </button>
            </div>

            <div class="order-items">
                ${o.items.map(i => `
                    <div class="order-row">
                        <span>${i.name}</span>

                        <span class="qty ${i.qty == 0 ? 'out' : ''}">
                           Out of Stock
                        </span>
                    </div>
                `).join("")}
            </div>

        </div>
    `).join("");
}
// Close modals on backdrop click
document.querySelectorAll(".modal-backdrop").forEach(el => {
    el.addEventListener("click", () => el.classList.remove("active"));
});

// Init
async function deleteBill(id) {

    if (!confirm("Delete this bill?")) return;

    await api(
        `/api/bills/${id}?shop_id=${localStorage.getItem("shop_id")}`,
        {
            method: "DELETE"
        }
    );

    await loadBills();

    await loadCustomers();

    await loadDashboard();
}
async function deleteOrder(id) {
    if (!confirm("Delete this order?")) return;

    await api(`/api/orders/${id}`, { method: "DELETE" });

    loadOrders();
}
function toggleOrder(id) {
    const el = document.getElementById("order-" + id);
    el.style.display = el.style.display === "none" ? "block" : "none";
}
async function deleteAllOrders() {
    if (!confirm("Delete ALL orders?")) return;

    const res = await fetch("/api/orders", {
        method: "DELETE"
    });

    const data = await res.json();
    console.log("DELETE ORDERS:", data);

    loadOrders(); // refresh UI
}
async function deleteAllBills() {
    if (!confirm("Delete ALL bills?")) return;

    const res = await fetch(
    `/api/bills?shop_id=${localStorage.getItem("shop_id")}`,
{
        method: "DELETE"
    });

    const data = await res.json();
    console.log("DELETE BILLS:", data);

    loadBills();
    await loadCustomers();
    await loadDashboard();
}
async function registerUser() {

    const body = {

        shop_name:
            document.getElementById(
                "reg-shop"
            ).value,

        owner_name:
            document.getElementById(
                "reg-owner"
            ).value,

        phone:
            document.getElementById(
                "reg-phone"
            ).value,

        address:
            document.getElementById(
                "reg-address"
            ).value,

        username:
            document.getElementById(
                "reg-username"
            ).value,

        password:
            document.getElementById(
                "reg-password"
            ).value
    };

    const res = await api(
        "/api/register",
        {

            method: "POST",

            headers: {
                "Content-Type":
                    "application/json"
            },

            body: JSON.stringify(body)
        }
    );

    if (res.error) {

        alert(res.error);

        return;
    }

    alert("Registration successful");
}


async function loginUser() {

    const body = {

        username:
            document.getElementById(
                "login-username"
            ).value,

        password:
            document.getElementById(
                "login-password"
            ).value
    };

    const res = await api(
        "/api/login",
        {

            method: "POST",

            headers: {
                "Content-Type":
                    "application/json"
            },

            body: JSON.stringify(body)
        }
    );

    if (res.error) {

        alert(res.error);

        return;
    }

    // SAVE LOGIN DATA

    localStorage.setItem(
        "shop_id",
        res.shop.id
    );

    localStorage.setItem(
        "user_id",
        res.user.id
    );

    localStorage.setItem(
        "username",
        res.user.username
    );

    localStorage.setItem(
    "login_time",
    Date.now()
    );

    // HIDE LOGIN

    document.getElementById(
        "auth-screen"
    ).style.display = "none";

    // SHOW APP

    document.getElementById(
        "main-app"
    ).style.display = "block";

    // OPEN DASHBOARD

    // LOAD DATA
await loadDashboard();

await loadAnalytics();

await loadMedicines();

await loadBills();

await loadOrders();

await loadWholesalers();

await loadSettings();

navigate("dashboard");
}


async function checkLogin() {

    const loginTime =
    localStorage.getItem(
        "login_time"
    );

if (
    loginTime &&
    Date.now() - loginTime > SESSION_TIME
) {

    logoutUser();

    return;
}

    const shopId =
        localStorage.getItem(
            "shop_id"
        );

    if (shopId) {

        // USER LOGGED IN

        document.getElementById(
            "auth-screen"
        ).style.display = "none";

        document.getElementById(
            "main-app"
        ).style.display = "block";

        await loadDashboard();

        await loadAnalytics();

        await loadMedicines();

        await loadBills();

        await loadOrders();

        await loadWholesalers();

        await loadSettings();

        navigate("dashboard");
    } else {

    document.getElementById(
        "auth-screen"
    ).style.display = "flex";

    document.getElementById(
        "main-app"
    ).style.display = "none";

}
}

function toggleTheme() {

    const current =
        document.documentElement.getAttribute(
            "data-theme"
        );

    const next =
        current === "dark"
            ? "light"
            : "dark";

    document.documentElement.setAttribute(
        "data-theme",
        next
    );

    localStorage.setItem(
        "theme",
        next
    );

    const btn =
        document.getElementById(
            "themeBtn"
        );

    if (btn) {

        btn.innerHTML =
            next === "dark"
                ? "☀️"
                : "🌙";
    }
}

loadTheme();

checkLogin();
function logoutUser() {

    localStorage.removeItem(
        "shop_id"
    );

    localStorage.removeItem(
        "user_id"
    );

    localStorage.removeItem(
        "username"
    );

    localStorage.removeItem(
        "login_time"
    );

    location.reload();
}
function closeBillModal() {

    document.getElementById(
        "bill-modal"
    ).classList.remove("active");
}
async function loadSettings() {

    const savedLogo =
    localStorage.getItem(
        "shop_logo"
    );

if (savedLogo){

    const preview =
        document.getElementById(
            "shop-logo-preview"
        );

    preview.src =
        savedLogo;

    preview.style.display =
        "block";

    document.getElementById(
        "shop-logo-plus"
    ).style.display =
        "none";

    document.getElementById(
        "remove-shop-logo"
    ).style.display =
        "flex";
}

    const shopId =
        localStorage.getItem(
            "shop_id"
        );

    if (!shopId) return;

    const data = await api(
        `/api/shop-profile/${shopId}`
    );

    SHOP_PROFILE = data;

    if (data.error) return;

    // FILL FORM

    document.getElementById(
        "setting-shop-name"
    ).value =
        data.shop_name || "";

    document.getElementById(
        "setting-owner-name"
    ).value =
        data.owner_name || "";

    document.getElementById(
        "setting-phone"
    ).value =
        data.phone || "";

    document.getElementById(
        "setting-address"
    ).value =
        data.address || "";

    document.getElementById(
        "setting-gst"
    ).value =
        data.gst_number || "";

    document.getElementById(
        "setting-business-type"
    ).value =
        data.business_type || "";

// BROWSER TITLE

// BROWSER TITLE

document.title =
    "MedicoSaathi";

const brand =
    document.querySelector(
    ".brand-tagline"
).textContent =
    "Trusted Pharma Network";

}


async function saveSettings() {

    const shopId =
        localStorage.getItem(
            "shop_id"
        );

        const logoFile =
    document.getElementById(
        "shop-logo"
    )?.files?.[0];

if (logoFile){

    const reader =
        new FileReader();

    reader.onload =
        function(e){

        localStorage.setItem(
            "shop_logo",
            e.target.result
        );
    };

    reader.readAsDataURL(
        logoFile
    );
}

    const body = {

        shop_name:
            document.getElementById(
                "setting-shop-name"
            ).value,

        owner_name:
            document.getElementById(
                "setting-owner-name"
            ).value,

        phone:
            document.getElementById(
                "setting-phone"
            ).value,

        address:
            document.getElementById(
                "setting-address"
            ).value,

        gst_number:
            document.getElementById(
                "setting-gst"
            ).value,
            
            upi_id:
    document.getElementById(
        "shop-upi"
    )?.value || "",

        business_type:
            document.getElementById(
                "setting-business-type"
            ).value
    };

    const res = await api(
        `/api/shop-profile/${shopId}`,
        {

            method: "POST",

            headers: {
                "Content-Type":
                    "application/json"
            },

            body: JSON.stringify(body)
        }
    );

    if (res.error) {

        alert(res.error);

        return;
    }

    alert(
        "Shop profile updated"
    );

    loadSettings();
}

window.salesChart = null;

async function loadAnalytics() {

    const data = await api(

        `/api/analytics?shop_id=${localStorage.getItem("shop_id")}`
    );

    const revenue = data.revenue || {};

    const labels = Object.keys(revenue);

    const values = Object.values(revenue);


    const ctx =
        document.getElementById(
            "salesChart"
        );

    if (!ctx) return;

    // DESTROY OLD CHART

    if (

        window.salesChart &&
        typeof window.salesChart.destroy === "function"

    ) {

        window.salesChart.destroy();
    }

    window.salesChart = new Chart(

        ctx,

        {

            type: "line",

            data: {

                labels,
                
datasets: [{

    label: "Revenue",

    data: values,

    tension: 0.45,

    fill: false,

    borderColor: "#38bdf8",

    backgroundColor: "#38bdf8",

    pointBackgroundColor: "#38bdf8",

    pointBorderColor: "#38bdf8",

    pointHoverBackgroundColor: "#ffffff",

    pointHoverBorderColor: "#38bdf8",

    pointRadius: 5,

    pointHoverRadius: 8,

    pointHoverBorderWidth: 4,

    borderWidth: 5
}]
            },

       options: {

    responsive: true,

    plugins: {

    legend: {

        labels: {

            color: "#94a3b8",

            usePointStyle: true,

            pointStyle: "line",

            boxWidth: 40,

            padding: 20,

            font: {
                size: 14,
                weight: "600"
            }
        }
    }
},

    scales: {

        x: {

            ticks: {

                color: "#94a3b8"
            },

            grid: {

                color: "rgba(148,163,184,0.08)"
            }
        },

        y: {

            ticks: {

                color: "#94a3b8"
            },

            grid: {

                color: "rgba(148,163,184,0.08)"
            }
        }
    }
},

            plugins: [

                {

                    id: "shadowLine",

                    beforeDatasetDraw(chart) {

                        const ctx = chart.ctx;

                        ctx.save();

                        ctx.shadowColor =
                            "rgba(0,0,0,0.18)";

                        ctx.shadowBlur = 16;

                        ctx.shadowOffsetY = 8;
                    },

                    afterDatasetDraw(chart) {

                        chart.ctx.restore();
                    }
                }
            ]
        }
    );

// TOP MEDICINES

const top =
    data.top_medicines || [];

const topEl =
    document.getElementById(
        "top-medicines"
    );

if (topEl) {

    if (!top.length) {

        topEl.innerHTML = `
            <div class="empty-analytics">
                No medicine sales yet
            </div>
        `;

    } else {

        topEl.innerHTML = top.map(m => `

            <div class="analytics-row-item">

                <span>
                    ${m[0]}
                </span>

                <strong>
                    ${m[1]} Sold
                </strong>

            </div>

        `).join("");

    }
}

// OVERSTOCK RISK

const overstockEl =
    document.getElementById(
        "overstock-risk"
    );

if (overstockEl) {

    overstockEl.innerHTML =
        data.dead_stock || 0;
}


// DEAD STOCK

const deadStockEl =
    document.getElementById(
        "dead-stock"
    );

if (deadStockEl) {

    deadStockEl.innerHTML = `
        ${(data.dead_stock || 0)}
        medicines have high stock
    `;
}
}
function setThermalMode() {

    const bill =
        document.querySelector(".bill");

    if (!bill) return;

    bill.className =
        "bill thermal-bill";
}

function setA4Mode() {

    const bill = document.querySelector(".bill");

    if (!bill) return;

    bill.classList.add(
        "a4-bill"
    );

    bill.classList.remove(
        "thermal-bill"
    );
}
function previewShopLogo(event){

    const file =
        event.target.files[0];

    if (!file) return;

    const reader =
        new FileReader();

    reader.onload =
        function(e){

        const preview =
            document.getElementById(
                "shop-logo-preview"
            );

        preview.src =
            e.target.result;

        preview.style.display =
            "block";


        document.getElementById(
    "remove-shop-logo"
).style.display =
    "flex";

        document.getElementById(
            "shop-logo-plus"
        ).style.display =
            "none";

        localStorage.setItem(
            "shop_logo",
            e.target.result
        );
    };

    reader.readAsDataURL(file);
}
function removeShopLogo(event){

    event.stopPropagation();

    localStorage.removeItem(
        "shop_logo"
    );

    document.getElementById(
        "shop-logo-preview"
    ).style.display =
        "none";

    document.getElementById(
        "shop-logo-plus"
    ).style.display =
        "flex";

    document.getElementById(
        "remove-shop-logo"
    ).style.display =
        "none";

    document.getElementById(
        "shop-logo"
    ).value = "";
}
function downloadInvoicePDF() {

    const invoice =
        document.querySelector(
            ".bill"
        );

    if (!invoice) {

        alert(
            "Invoice not found"
        );

        return;
    }

    const opt = {

        margin: 0.3,

        filename:
            `Invoice-${Date.now()}.pdf`,

        image: {
            type: "jpeg",
            quality: 1
        },

        html2canvas: {
            scale: 2
        },

        jsPDF: {

            unit: "in",

            format: "a4",

            orientation: "portrait"
        }
    };

    html2pdf()
        .set(opt)
        .from(invoice)
        .save();
}
let customerCache = [];
async function loadCustomers() {

    try{

        const response =
            await fetch(
                `/api/customers?shop_id=${localStorage.getItem("shop_id")}`
            );

        const data =
            await response.json();
            
        customerCache =
        data.customers || [];

        document.getElementById(
            "total-customers"
        ).textContent =
            data.total_customers || 0;

        document.getElementById(
            "total-due"
        ).textContent =
            `₹${data.total_due || 0}`;

        document.getElementById(
            "paid-customers"
        ).textContent =
            data.paid_customers || 0;

        document.getElementById(
            "due-customers"
        ).textContent =
            data.due_customers || 0;

        const tbody =
            document.getElementById(
                "customer-table-body"
            );

        tbody.innerHTML = "";

        if (
            !data.customers?.length
        ) {

            tbody.innerHTML = `
                <tr>
                    <td colspan="6">
                        No customer records
                    </td>
                </tr>
            `;

            return;
        }

        data.customers.forEach(
            customer => {

                tbody.innerHTML += `
                    <tr>

                        <td>
                            ${customer.name}
                        </td>

                        <td>
                            ${customer.phone}
                        </td>

                        <td>
    ${
        customer.last_purchase
        ? new Date(
            customer.last_purchase
        ).toLocaleString(
            "en-IN",
            {
                day: "2-digit",
                month: "short",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit"
            }
        )
        : "-"
    }
</td>
                        <td>
                            ₹${customer.total_due}
                        </td>

                        <td>

                            <span class="
                                customer-status
                                ${
                                    customer.total_due > 0
                                    ? "due"
                                    : "paid"
                                }
                            ">

                                ${
                                    customer.total_due > 0
                                    ? "Due"
                                    : "Paid"
                                }

                            </span>

                        </td>
                        <td>

    <button
        class="customer-delete-btn"
        onclick="deleteCustomer(${customer.id})"
    >

        Delete

    </button>

</td>

                    </tr>
                `;
            }
        );

    }catch(error){

        console.log(error);
    }
}
async function loadCustomerAnalytics(){

    const shopId =
        localStorage.getItem(
            "shop_id"
        );

    const data = await api(
        `/api/customers/analytics?shop_id=${shopId}`
    );

    const topEl =
        document.getElementById(
            "top-customers-list"
        );

    const dueEl =
        document.getElementById(
            "highest-due-list"
        );

    // TOP CUSTOMERS

    if(topEl){

        if(
            !data.top_customers ||
            !data.top_customers.length
        ){

            topEl.innerHTML =
                `<div class="empty-analytics">
                    No repeat customers
                </div>`;

        }else{

            topEl.innerHTML =
            data.top_customers.map(c => `

                <div class="analytics-row-item">

                    <div>

                        <div class="customer-name">
                            ${c.name}
                        </div>

                        <div class="customer-visits">
                            ${c.visits} Visits
                        </div>

                    </div>

                    <strong>
                        ₹${c.total_purchase}
                    </strong>

                </div>

            `).join("");
        }
    }

    // HIGHEST DUE

    if(dueEl){

        if(
            !data.highest_due ||
            !data.highest_due.length
        ){

            dueEl.innerHTML =
                `<div class="empty-analytics">
                    No dues above ₹100
                </div>`;

        }else{

            dueEl.innerHTML =
            data.highest_due.map(c => `

                <div class="analytics-row-item">

                    <span>
                        ${c.name}
                    </span>

                    <strong>
                        ₹${c.due}
                    </strong>

                </div>

            `).join("");
        }
    }
}
function filterCustomers() {

    const query =
        document
        .getElementById(
            "customer-search"
        )
        ?.value
        .trim()
        .toLowerCase();

    const filtered =
        customerCache.filter(c =>

            (c.name || "")
                .toLowerCase()
                .includes(query)

            ||

            (c.phone || "")
                .toLowerCase()
                .includes(query)

        );

    renderCustomers(
        filtered
    );
}
function renderCustomers(customers) {

    const tbody =
        document.getElementById(
            "customer-table-body"
        );

    tbody.innerHTML = "";

    if (!customers.length) {

        tbody.innerHTML = `
            <tr>
                <td colspan="6">
                    No customer records found
                </td>
            </tr>
        `;

        return;
    }

    customers.forEach(customer => {

        tbody.innerHTML += `
            <tr>

                <td>
                    ${customer.name}
                </td>

                <td>
                    ${customer.phone}
                </td>

                <td>
                    ${
                        customer.last_purchase
                        ? new Date(
                            customer.last_purchase
                        ).toLocaleString(
                            "en-IN",
                            {
                                day: "2-digit",
                                month: "short",
                                year: "numeric",
                                hour: "2-digit",
                                minute: "2-digit"
                            }
                        )
                        : "-"
                    }
                </td>

                <td>
                    ₹${customer.total_due}
                </td>

                <td>

                    <span class="
                        customer-status
                        ${
                            customer.total_due > 0
                            ? "due"
                            : "paid"
                        }
                    ">

                        ${
                            customer.total_due > 0
                            ? "Due"
                            : "Paid"
                        }

                    </span>

                </td>

                <td>

                    <button
                        class="customer-delete-btn"
                        onclick="deleteCustomer(${customer.id})"
                    >

                        Delete

                    </button>

                </td>

            </tr>
        `;
    });
}
async function deleteCustomer(id){

    const confirmDelete =
        confirm(
            "Delete this customer?"
        );

    if(!confirmDelete) return;

    try{

        const response =
            await fetch(

                `/api/customers/${id}?shop_id=${localStorage.getItem("shop_id")}`,

                {
                    method:"DELETE"
                }
            );

        const data =
            await response.json();

        if(data.success){

    await loadCustomers();
    await loadCustomerAnalytics();
    await loadDashboard();
    await loadBills();

    showToast(
        "Customer deleted",
        "success"
    );

        }else{

            showToast(
                "Delete failed",
                "error"
            );
        }

    }catch(error){

        console.log(error);

        showToast(
            "Server error",
            "error"
        );
    }
}
const paidInput =
    document.getElementById(
        "paidAmount"
    );

if(paidInput){

    paidInput.addEventListener(

        "input",

        updateDueAmount
    );
}
let selectedUpiApp = "";

function showToast(message, type = "success") {

    const toast = document.createElement("div");

    toast.className = `toast toast-${type}`;

    toast.innerText = message;

    document.body.appendChild(toast);

    setTimeout(() => {

        toast.classList.add("show");

    }, 100);

    setTimeout(() => {

        toast.classList.remove("show");

        setTimeout(() => {

            toast.remove();

        }, 300);

    }, 2500);
}
function formatExportDate(dateString){

    if(!dateString) return "";

    const d = new Date(dateString);

    return d.toLocaleString(
        "en-IN",
        {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit"
        }
    );
}
function exportCustomersCSV() {

    if (!customerCache.length) {

        alert(
            "No customers found"
        );

        return;
    }

    let csv =
        "Name,Phone,Due,Last Purchase\n";

    customerCache.forEach(c => {

    csv +=
        `"${c.name || ""}",` +
        `"${c.phone || ""}",` +
        `"${c.total_due || 0}",` +
        `"${formatExportDate(c.last_purchase)}"\n`;

});

    const blob =
        new Blob(
            [csv],
            {
                type:
                "text/csv;charset=utf-8;"
            }
        );

    const url =
        URL.createObjectURL(blob);

    const link =
        document.createElement("a");

    link.href = url;

    link.download =
        `customers_${new Date()
            .toISOString()
            .split("T")[0]}.csv`;

    document.body.appendChild(
        link
    );

    link.click();

    document.body.removeChild(
        link
    );

    URL.revokeObjectURL(url);
}