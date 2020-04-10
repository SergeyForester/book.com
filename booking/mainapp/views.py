import datetime

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from mainapp.models import Hotel, Room, Bookings, RoomGallery, Comment
from mainapp.utils import check_booking, insert_booking, get_coordinates


def main_page(request):
    user = request.user

    return render(request, 'mainapp/index.html', {'user': user})


def bookings_main(request, hotel_id):
    hotel = get_object_or_404(Hotel, pk=hotel_id)
    rooms = Room.objects.filter(hotel=hotel, is_active=True)
    days = [datetime.date.today() + datetime.timedelta(days=dayR) for dayR in range(14)]
    images = RoomGallery.objects.filter(room__hotel=hotel, is_avatar=True)
    coordinates = get_coordinates(hotel.location)
    comments = Comment.objects.order_by('-pub_date')[:5]

    content = {
        'hotel': hotel,
        'rooms': rooms,
        'days': days,
        'coordinates': coordinates,
        'images': images,
        'comments': comments
    }

    return render(request, 'mainapp/booking_main.html', content)


def book_room(request, hotel_id, room_id):
    user = request.user
    hotel = get_object_or_404(Hotel, pk=hotel_id)
    room = get_object_or_404(Room, hotel=hotel, pk=room_id, is_active=True)
    days = [datetime.date.today() + datetime.timedelta(days=dayR) for dayR in range(14)]
    total = None
    if request.method == 'POST':
        check_in = request.POST.get('start', None)
        check_out = request.POST.get('end', None)
        client_name = request.POST.get('client_name', None)
        client_surname = request.POST.get('client_surname', None)
        email = request.POST.get('email', None)
        phone = request.POST.get('phone', None)
        time = request.POST.get('time', None)
        comments = request.POST.get('comments', None)
        country = request.POST.get('country', None)
        address = request.POST.get('address', None)
        print(check_in, check_out, client_name, client_surname, email, phone, time, comments, country, address)

        if check_booking(check_in, check_out, room_id, hotel_id):  # if there are not any reservations
            insert_booking(hotel, check_in, check_out, room, f'{client_name} {client_surname}', email, phone, time,
                           comments, country, address)
            # send_confirmation_mail(hotel_id, room_id, check_in, check_out, f'{client_name}:{client_surname}')
            # ":" is just separator
            return HttpResponseRedirect(reverse('order:pay',
                                                kwargs={
                                                    'hotel_id': hotel_id,
                                                    'room_id': room_id,
                                                    'check_in': check_in,
                                                    'check_out': check_out
                                                }))
        else:
            messages.error(request, 'This room is not available at this period')

    images = RoomGallery.objects.filter(room__hotel=hotel, room=room)
    coordinates = get_coordinates(room.hotel.location)

    print(room.hotel.location)
    print(coordinates)
    content = {
        'user': user,
        'hotel': hotel,
        'room': room,
        'days': days,
        'coordinates': coordinates,
        'summ': total,
        'images': images
    }
    return render(request, 'mainapp/book_room.html', content)


def total_sum(hotel_id, room_id, check_in, check_out):
    booking = get_object_or_404(Bookings, hotel__pk=hotel_id, room__pk=room_id, date=check_in)

    start = datetime.datetime.strptime(check_in, "%Y-%m-%d")
    end = datetime.datetime.strptime(check_out, "%Y-%m-%d")
    date_list = [start + datetime.timedelta(days=x) for x in range(0, (end - start).days + 1)]
    total = sum([booking.room.price for x in range(len(date_list))])
    return total


def send_confirmation_mail(hotel_id, room_id, check_in, check_out, client_name):
    print('send_confirmation_mail')
    booking = get_object_or_404(Bookings, hotel__pk=hotel_id, room__pk=room_id, date=check_in)
    start = datetime.datetime.strptime(check_in, "%Y-%m-%d")
    end = datetime.datetime.strptime(check_out, "%Y-%m-%d")
    date_list = [start + datetime.timedelta(days=x) for x in range(0, (end - start).days + 1)]

    total = sum([booking.room.price for x in range(len(date_list))])

    data = {'booking': booking, 'nights': len(date_list), 'first_name': booking.client_name.split(':')[0],
            'check_in': check_in, 'check_out': check_out, 'total': total, 'domain': settings.DOMAIN_NAME,
            'coordinates': str(get_coordinates(booking.hotel.location))}
    print(data)

    html_m = render_to_string('mainapp/confirmation_letter.html', data)

    return send_mail('Booking Confirmation', '', settings.EMAIL_HOST_USER,
                     [booking.client_email], html_message=html_m, fail_silently=False)


def add_comment(request, hotel_id):
    try:
        hotel = Hotel.objects.get(id=hotel_id)
    except:
        Http404('Отель не найден!')

    hotel.comment_set.create(author=request.POST['name'], comment=request.POST['text'])

    return HttpResponseRedirect(reverse('main:bookings_main', args=(hotel.id,)))
