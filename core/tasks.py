from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Persona
from django.db.models import Q
import requests
import os
from datetime import datetime
from instagrapi import Client


@shared_task
def update_outdated_personas():
    """
    Task to update Personas that haven't been updated in the last 24 hours.
    Runs every hour via Celery Beat.
    """
    # Find Personas not updated in the last 24 hours
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    outdated_personas = Persona.objects.filter(
        Q(last_updated__lt=twenty_four_hours_ago) | Q(last_updated__isnull=True))
    print(outdated_personas)
    # Process each outdated Persona
    for persona in outdated_personas:
        try:
            update_persona(persona)
        except Exception as e:
            # Log any errors during update
            print(f"Error updating Persona {persona.id}: {str(e)}")


def update_persona(persona):
    life_update = generate_life_update(persona.biography)
    image = generate_image(persona.character)
    print(image)
    upload_to_instagram(persona, image, life_update)
    persona.last_updated = timezone.now()
    persona.save()


def generate_life_update(biography):
    url = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-3B-Instruct/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = (
        f"{biography}\n"
        f"please write a litle action to share for this biography. like today we are at home, or we went to the cinema etc. just 1 sentence. and just answer, without description"
    )

    data = {
        "model": "meta-llama/Llama-3.2-3B-Instruct",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        update = response.json()["choices"][0]["message"]["content"]
        print('[life update]', update)
        return update
    else:
        raise Exception(f"Life Update generation failed: {response.text}")


def generate_image(character):
    """Generate avatar using HuggingFace API"""
    url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"
    headers = {
        "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
    }

    avatar_prompt = f"Generate ultrarealistic image of young woman. {
        character}"
    data = {"inputs": avatar_prompt}

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        # Create media directory if it doesn't exist
        temp_dir = 'temp'
        os.makedirs(temp_dir, exist_ok=True)

        # Save the image temporarily
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(temp_dir, f"generated_avatar_{timestamp}.jpg")

        with open(filename, "wb") as f:
            f.write(response.content)

        return filename
    else:
        raise Exception(f"Avatar generation failed: {response.text}")


def upload_to_instagram(persona, image, caption):
    # Initialize Instagram client
    instagram_client = Client()
    instagram_client.login(
        persona.username,
        persona.password
    )

    instagram_client.photo_upload(image, caption=caption)
