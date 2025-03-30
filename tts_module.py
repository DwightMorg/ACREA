# tts_module.py

import logging
import os
from google.cloud import texttospeech
from google.api_core import exceptions as google_exceptions
import uuid # For unique filenames

class TTSModule:
    """
    Handles text synthesis using Google Cloud Text-to-Speech API.
    Saves the synthesized audio to a file.
    """
    def __init__(self, project_id: str = None,
                 default_language_code: str = "en-US",
                 default_voice_name: str = "en-US-Standard-C",
                 default_audio_encoding = texttospeech.AudioEncoding.MP3,
                 output_directory: str = "audio_cache"):
        """
        Initializes the TTS client and configuration.

        Args:
            project_id: Optional GCP Project ID. If None, inferred from ADC.
            default_language_code: Default language code (e.g., "en-US", "pl-PL").
            default_voice_name: Default voice name (e.g., "en-US-Standard-C", "pl-PL-Chirp3-HD-Leda").
            default_audio_encoding: Default encoding (MP3 is recommended for playback).
            output_directory: Folder where synthesized audio files will be saved.
        """
        self.logger = logging.getLogger("TTSModule")
        self.default_language_code = default_language_code
        self.default_voice_name = default_voice_name
        self.default_audio_encoding = default_audio_encoding
        self.output_directory = output_directory

        try:
            # Instantiate the client. ADC is used automatically.
            # Pass project_id if provided, otherwise library attempts to infer.
            client_options = {"quota_project_id": project_id} if project_id else None
            self.client = texttospeech.TextToSpeechClient(client_options=client_options)
            self.logger.info(f"TTSModule initialized. Project: {project_id or 'inferred'}. Default Voice: {self.default_voice_name}")

            # Create output directory if it doesn't exist
            if not os.path.exists(self.output_directory):
                os.makedirs(self.output_directory)
                self.logger.info(f"Created output directory: {self.output_directory}")

        except google_exceptions.GoogleAPICallError as e:
             self.logger.error(f"Failed to initialize TTS client (Check API enabled & ADC?): {e}", exc_info=True)
             raise # Re-raise critical initialization error
        except Exception as e:
            self.logger.error(f"Failed to initialize TTSModule: {e}", exc_info=True)
            raise

    def _synthesize_speech(self, text_or_ssml: str, output_filename: str,
                           language_code: str, voice_name: str,
                           audio_encoding) -> str | None:
        """Internal method to perform the synthesis and save the file."""
        try:
            # Determine if input is SSML or plain text
            # Simple check: if it starts with '<speak>' assume SSML
            if text_or_ssml.strip().startswith("<speak>"):
                 synthesis_input = texttospeech.SynthesisInput(ssml=text_or_ssml)
                 input_type = "SSML"
            else:
                 synthesis_input = texttospeech.SynthesisInput(text=text_or_ssml)
                 input_type = "Text"

            # Set the voice parameters
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code, name=voice_name
            )

            # Select the type of audio file you want
            audio_config = texttospeech.AudioConfig(
                audio_encoding=audio_encoding
                # You can add speaking_rate, pitch etc. here if needed
            )

            self.logger.info(f"Synthesizing {input_type} (Voice: {voice_name}, Lang: {language_code})...")
            # Perform the text-to-speech request
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            # Ensure output path is within the designated directory
            output_path = os.path.join(self.output_directory, os.path.basename(output_filename))

            # The response's audio_content is binary.
            with open(output_path, "wb") as out:
                out.write(response.audio_content)
                self.logger.info(f"Audio content written to file: {output_path}")

            return output_path # Return the full path to the saved file

        except google_exceptions.InvalidArgument as e:
            self.logger.error(f"TTS Invalid Argument (check text/ssml, voice name?): {e}", exc_info=True)
            return None
        except google_exceptions.GoogleAPICallError as e:
            self.logger.error(f"TTS API Call Error (check quota, permissions?): {e}", exc_info=True)
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during TTS synthesis: {e}", exc_info=True)
            return None

    def handle_message(self, action: str, payload: dict):
        """Handles actions directed to the TTS module."""
        if action == "synthesize_speech":
            text_input = payload.get("text") # Prioritize plain text
            ssml_input = payload.get("ssml") # Allow SSML override
            output_filename_base = payload.get("output_filename", f"tts_output_{uuid.uuid4()}")

            # Determine input content
            content_to_synth = ssml_input if ssml_input else text_input
            if not content_to_synth:
                self.logger.error("Synthesize speech action missing 'text' or 'ssml' in payload.")
                return {"success": False, "error": "Missing input text/ssml", "output_path": None}

            # Determine filename and encoding (use defaults if not provided)
            language_code = payload.get("language_code", self.default_language_code)
            voice_name = payload.get("voice_name", self.default_voice_name)
            audio_encoding_enum = payload.get("audio_encoding", self.default_audio_encoding)
            # Ensure it's the enum type if passed as string (simple check)
            if isinstance(audio_encoding_enum, str):
                try:
                    audio_encoding_enum = texttospeech.AudioEncoding[audio_encoding_enum.upper()]
                except KeyError:
                    self.logger.warning(f"Invalid audio encoding string '{audio_encoding_enum}', using default MP3.")
                    audio_encoding_enum = texttospeech.AudioEncoding.MP3

            # Determine file extension based on encoding
            extension = ".mp3" # Default for MP3
            if audio_encoding_enum == texttospeech.AudioEncoding.LINEAR16:
                 extension = ".wav" # Or .raw
            elif audio_encoding_enum == texttospeech.AudioEncoding.OGG_OPUS:
                 extension = ".ogg"

            # Construct unique output filename
            output_filename = f"{output_filename_base}{extension}"

            # Call the internal synthesis method
            output_path = self._synthesize_speech(
                text_or_ssml=content_to_synth,
                output_filename=output_filename,
                language_code=language_code,
                voice_name=voice_name,
                audio_encoding=audio_encoding_enum
            )

            if output_path:
                return {"success": True, "output_path": output_path, "error": None}
            else:
                return {"success": False, "output_path": None, "error": "Synthesis failed. Check logs."}

        else:
            self.logger.warning(f"TTSModule received unknown action: {action}")
            return {"success": False, "error": f"Unknown action: {action}", "output_path": None}