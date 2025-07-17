// Orders Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Cancel Order Modal
    const cancelOrderModal = document.getElementById('cancelOrderModal');
    if (cancelOrderModal) {
        cancelOrderModal.addEventListener('show.bs.modal', function(event) {
            // Button that triggered the modal
            const button = event.relatedTarget;
            // Extract order ID from data-* attributes
            const orderId = button.getAttribute('data-order-id');
            
            // Update the modal's content
            const modalTitle = cancelOrderModal.querySelector('.modal-title');
            modalTitle.textContent = `Cancel Order #${orderId}`;
            
            // Set the order ID in the form for submission
            const form = document.getElementById('cancelOrderForm');
            if (!form.dataset.orderId) {
                const orderIdInput = document.createElement('input');
                orderIdInput.type = 'hidden';
                orderIdInput.name = 'order_id';
                orderIdInput.value = orderId;
                form.appendChild(orderIdInput);
            } else {
                form.dataset.orderId = orderId;
            }
        });
        
        // Handle cancel order form submission
        const confirmCancelBtn = document.getElementById('confirmCancelBtn');
        confirmCancelBtn.addEventListener('click', function() {
            const form = document.getElementById('cancelOrderForm');
            const reason = document.getElementById('cancelReason').value;
            
            if (!reason) {
                alert('Please select a reason for cancellation');
                return;
            }
            
            // In a real application, you would submit this to the server
            // For now, we'll just show a success message and close the modal
            alert('Order cancellation request submitted');
            
            // Close the modal
            const modal = window.bootstrap.Modal.getInstance(cancelOrderModal);
            modal.hide();
            
            // Refresh the page or update the UI
            // window.location.reload();
        });
    }
    
    // Review Order Modal
    const reviewOrderModal = document.getElementById('reviewOrderModal');
    if (reviewOrderModal) {
        reviewOrderModal.addEventListener('show.bs.modal', function(event) {
            // Button that triggered the modal
            const button = event.relatedTarget;
            // Extract order ID from data-* attributes
            const orderId = button.getAttribute('data-order-id');
            
            // Update the modal's content
            const modalTitle = reviewOrderModal.querySelector('.modal-title');
            modalTitle.textContent = `Review Order #${orderId}`;
            
            // Reset the form
            document.getElementById('reviewForm').reset();
            document.getElementById('ratingValue').value = 0;
            
            // Reset stars
            const stars = document.querySelectorAll('.rating i');
            stars.forEach(star => star.className = 'far fa-star');
            
            // Set the order ID in the form for submission
            const form = document.getElementById('reviewForm');
            if (!form.dataset.orderId) {
                const orderIdInput = document.createElement('input');
                orderIdInput.type = 'hidden';
                orderIdInput.name = 'order_id';
                orderIdInput.value = orderId;
                form.appendChild(orderIdInput);
            } else {
                form.dataset.orderId = orderId;
            }
        });
        
        // Handle review form submission
        const submitReviewBtn = document.getElementById('submitReviewBtn');
        submitReviewBtn.addEventListener('click', function() {
            const form = document.getElementById('reviewForm');
            const rating = document.getElementById('ratingValue').value;
            const title = document.getElementById('reviewTitle').value;
            const content = document.getElementById('reviewContent').value;
            
            if (rating === '0') {
                alert('Please select a rating');
                return;
            }
            
            if (!title) {
                alert('Please enter a review title');
                return;
            }
            
            if (!content) {
                alert('Please enter your review');
                return;
            }
            
            // In a real application, you would submit this to the server
            // For now, we'll just show a success message and close the modal
            alert('Review submitted successfully');
            
            // Close the modal
            const modal = window.bootstrap.Modal.getInstance(reviewOrderModal);
            modal.hide();
            
            // Refresh the page or update the UI
            // window.location.reload();
        });
    }
    
    // Order tracking animation
    const timelineItems = document.querySelectorAll('.timeline-item');
    timelineItems.forEach((item, index) => {
        setTimeout(() => {
            if (item.classList.contains('active')) {
                item.style.opacity = 0;
                item.style.transform = 'translateY(20px)';
                item.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                
                setTimeout(() => {
                    item.style.opacity = 1;
                    item.style.transform = 'translateY(0)';
                }, 100 * index);
            }
        }, 500);
    });
});