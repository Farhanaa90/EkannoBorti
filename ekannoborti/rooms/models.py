from django.db import models
from users.models import UserProfile

class Room(models.Model):
    posted_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    address = models.CharField(max_length=100)
    details = models.TextField(blank=True)
    monthly_price = models.FloatField()
    photo = models.ImageField(upload_to='rooms/', null=True, blank=True)
    is_available = models.BooleanField(default=True)
    posted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mess.mess_name} - {self.address}"


class RoomRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='requests')
    seeker = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='room_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.seeker.username} → {self.room}"