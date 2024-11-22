from django.shortcuts import render, redirect
from .models import Persona, ScheduledPost
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
import os
from django.core.files.base import ContentFile
from django.conf import settings
import requests
import threading
from datetime import datetime
from instagrapi import Client


def home(request):
    if request.method == 'POST':
        try:
            # Get form data
            username = request.POST.get('username')
            password = request.POST.get('password')
            industry = request.POST.get('industry')
            print('[username, password, industry]',
                  username, password, industry)

            # Generate biography
            biography, character = generate_biography(industry)

            # Generate avatar
            avatar_path = generate_avatar(character)

            # Create Persona object
            persona = Persona.objects.create(
                user=request.user,
                username=username,
                password=password,
                biography=biography,
                character=character
            )

            # Save the generated image
            with open(avatar_path, 'rb') as f:
                persona.avatar.save(
                    os.path.basename(avatar_path),
                    ContentFile(f.read()),
                    save=True
                )

            # Clean up the temporary image file
            os.remove(avatar_path)
            upload_to_instagram(persona)
            print("[completed]")
            return redirect('home')

        except Exception as e:
            # Log the error and return error response
            print(f"Error creating persona: {str(e)}")
            Persona.objects.filter(user=request.user).delete()
            return render(request, 'error.html', {
                'error_message': 'Failed to create persona. Please try again.'
            })

    return render(request, 'core/home.html')


def logout_view(request):
    """Handle user logout"""
    logout(request)
    return redirect('home')


def generate_biography(industry):
    """Generate biography using HuggingFace API"""
    url = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-3B-Instruct/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }

    bio_prompt = (
        f"Please write 1-2 paragraph biography of woman in industry {
            industry}. Contain "
        f"details like childhood background, achievements, and professional summary. "
        f"Example: Input: Target Industry = 'Writer' Output: 'I was born in 1997. "
        f"As a child, I was passionate about storytelling. Over the past 3 years, "
        f"I've authored several love stories...'"
        f"Give directly answer. don't start with Here is answer. just answer, "
        f"start like I am ..."
    )

    character_prompt = (f"please describe a young {industry} woman's face and hair in 2 sentences. example:"
                        "A young writer woman has a thoughtful and expressive face, often framed by wisps of hair that "
                        "escape her casual updo, reflecting her creative and introspective nature. Her eyes,bright and "
                        "inquisitive, are usually accentuated by subtle glasses, while her hair, "
                        "typically worn in a messy bun or loose waves, adds to her bohemian and intellectual charm.")

    data = {
        "model": "meta-llama/Llama-3.2-3B-Instruct",
        "messages": [{"role": "user", "content": bio_prompt}],
        "max_tokens": 300
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        biography = response.json()["choices"][0]["message"]["content"]
        print('[biography]', biography)
    else:
        raise Exception(f"Biography generation failed: {response.text}")

    data = {
        "model": "meta-llama/Llama-3.2-3B-Instruct",
        "messages": [{"role": "user", "content": character_prompt}],
        "max_tokens": 300
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        character = response.json()["choices"][0]["message"]["content"]
        print('[character]', character)
    else:
        raise Exception(f"Biography generation failed: {response.text}")

    return biography, character


def generate_avatar(character):
    """Generate avatar using HuggingFace API"""
    url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"
    headers = {
        "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
    }

    avatar_prompt = f"Generate a professional headshot photo of a young woman. {
        character}"
    data = {"inputs": avatar_prompt}

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        # Create media directory if it doesn't exist
        media_root = getattr(settings, 'MEDIA_ROOT', 'media')
        temp_dir = os.path.join(media_root, 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        # Save the image temporarily
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(temp_dir, f"generated_avatar_{timestamp}.jpg")

        with open(filename, "wb") as f:
            f.write(response.content)

        return filename
    else:
        raise Exception(f"Avatar generation failed: {response.text}")


def upload_to_instagram(persona):
    # Initialize Instagram client
    instagram_client = Client()
    instagram_client.login(
        persona.username,
        persona.password
    )

    instagram_client.account_change_picture(persona.avatar.path)
    instagram_client.photo_upload(
        persona.avatar.path,
        caption=persona.biography
    )
