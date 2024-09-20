// Sample chart using Chart.js
const ctx = document.getElementById('myChart').getContext('2d');

const myChart = new Chart(ctx, {
    type: 'line', // You can change this to 'bar', 'pie', 'radar', etc.
    data: {
        labels: ['January', 'February', 'March', 'April', 'May', 'June'], // X-axis labels
        datasets: [{
            label: 'Network Performance (Mbps)',
            data: [12, 19, 3, 5, 2, 3], // Y-axis data
            backgroundColor: 'rgba(75, 192, 192, 0.2)', // Fill color
            borderColor: 'rgba(75, 192, 192, 1)', // Line color
            borderWidth: 1
        }]
    },
    options: {
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});
function openNav() {
    document.getElementById("sidebar").style.width = "250px";
    document.getElementById("main").style.marginLeft = "250px";
}

function closeNav() {
    document.getElementById("sidebar").style.width = "0";
    document.getElementById("main").style.marginLeft= "0";
}
