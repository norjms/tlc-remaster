/*
 * AudioSystem on miniaudio (replaces FMOD Ex).
 *
 * Mapping from the FMOD version:
 *  - FMOD_SYSTEM            -> ma_engine (one per AudioSystem)
 *  - FMOD_SOUND + CHANNEL   -> ma_sound (one primary voice per Sample)
 *  - FMOD_CHANNEL_FREE      -> extra ma_sound voices, so the same effect
 *                              can overlap itself like it did under FMOD
 *  - FMOD_OUTPUTTYPE_NOSOUND-> engine == NULL; samples still "load" and
 *                              "play" successfully, they just make no sound
 *
 * IsPlaying() works again. Under FMOD it was disabled because of "stack
 * corruption"; the cause was casting a 1-byte bool* to FMOD's 4-byte
 * FMOD_BOOL*, not FMOD itself.
 */

//miniaudio declarations first, before Allegro's headers define int64_t
//and friends as macros
#include "thirdparty/miniaudio/miniaudio.h"

#include "env.h"			//for TRACE
#include "AudioSystem.h"
using namespace std;

// ---------------------------------------------------------------------
// Sample
// ---------------------------------------------------------------------

Sample::Sample():
	name(""),
	filename(""),
	loop(false),
	paused(false),
	streamed(false),
	volume(1.0f),
	owner(NULL),
	sound(NULL)
{
}

Sample::~Sample()
{
	//after AudioSystem shuts down, owner is NULL and the voices are gone
	if (owner != NULL)
	{
		ReleaseVoices();
		owner->Forget(this);
	}
}

void Sample::ReleaseVoices()
{
	for (size_t i = 0; i < extraVoices.size(); ++i)
	{
		ma_sound_uninit(extraVoices[i]);
		delete extraVoices[i];
	}
	extraVoices.clear();

	if (sound != NULL)
	{
		ma_sound_uninit(sound);
		delete sound;
		sound = NULL;
	}
}

/**
    volume is based on 1.0 = 100%
**/
void Sample::SetVolume(float vol)
{
	//perform a reasonable bounds check
	if (vol < 0.0f || vol > 10.0f) return;

	volume = vol;
	if (sound != NULL) ma_sound_set_volume(sound, volume);
	for (size_t i = 0; i < extraVoices.size(); ++i)
		ma_sound_set_volume(extraVoices[i], volume);
}

/*
 * doLoop == false --> oneshot playback
 * doLoop == true  --> playback will loop forever
 */
void Sample::SetLoop(bool doLoop)
{
	loop = doLoop;
	if (sound != NULL) ma_sound_set_looping(sound, doLoop ? MA_TRUE : MA_FALSE);
}

/*
 * pause/unpause the primary voice; stopping an ma_sound keeps its
 * cursor, so starting it again resumes where it left off
 */
void Sample::SetPaused(bool doPause)
{
	paused = doPause;
	if (sound == NULL) return;

	ma_result res = doPause ? ma_sound_stop(sound) : ma_sound_start(sound);
	if (res != MA_SUCCESS)
		debug << "AudioSystem: SetPaused(" << doPause << ") failed for " << filename << ": " << ma_result_description(res) << endl;
}

// ---------------------------------------------------------------------
// AudioSystem
// ---------------------------------------------------------------------

AudioSystem::AudioSystem(void):
	engine(NULL),
	bPlay(false)
{
}

AudioSystem::~AudioSystem(void)
{
	//release every voice while the engine still exists, then detach the
	//samples so anything deleted later (e.g. ModeMgr's music) is a no-op
	for (std::set<Sample*>::iterator i = live.begin(); i != live.end(); ++i)
	{
		(*i)->ReleaseVoices();
		(*i)->owner = NULL;
	}
	live.clear();

	//named samples belong to us
	for (SampleIterator i = samples.begin(); i != samples.end(); ++i)
		delete (*i);
	samples.clear();

	if (engine != NULL)
	{
		ma_engine_uninit(engine);
		delete engine;
		engine = NULL;
	}
}

bool AudioSystem::Init()
{
	//retrieve global audio playback setting
	bPlay = g_game->getGlobalBoolean("AUDIO_GLOBAL");

	if (!bPlay)
	{
		debug << "AudioSystem::Init: audio disabled by AUDIO_GLOBAL, running silent" << endl;
		return true;
	}

	engine = new ma_engine;
	ma_engine_config config = ma_engine_config_init();
	ma_result res = ma_engine_init(&config, engine);
	if (res != MA_SUCCESS)
	{
		//same fallback FMOD had: keep going with sound disabled
		debug << "AudioSystem::Init: ma_engine_init failed (" << ma_result_description(res) << "), running silent" << endl;
		delete engine;
		engine = NULL;
		return true;
	}

	debug << "AudioSystem::Init: miniaudio " << MA_VERSION_STRING << " on " << ma_engine_get_sample_rate(engine) << " Hz" << endl;
	return true;
}

/*
 * Once per frame: reclaim overlapping one-shot voices that have finished.
 * (miniaudio mixes on its own thread, so nothing else needs pumping.)
 */
void AudioSystem::Update()
{
	if (engine == NULL) return;

	for (std::set<Sample*>::iterator i = live.begin(); i != live.end(); ++i)
	{
		std::vector<ma_sound*> &voices = (*i)->extraVoices;
		size_t n = 0;
		while (n < voices.size())
		{
			if (!ma_sound_is_playing(voices[n]) && ma_sound_at_end(voices[n]))
			{
				ma_sound_uninit(voices[n]);
				delete voices[n];
				voices.erase(voices.begin() + n);
			}
			else ++n;
		}
	}
}

ma_sound *AudioSystem::CreateVoice(Sample *sample)
{
	if (engine == NULL) return NULL;

	//effects are decoded into memory once (the resource manager caches them
	//by file name, so extra voices share the data); music is streamed
	ma_uint32 flags = MA_SOUND_FLAG_NO_SPATIALIZATION;
	flags |= sample->streamed ? MA_SOUND_FLAG_STREAM : MA_SOUND_FLAG_DECODE;

	ma_sound *voice = new ma_sound;
	ma_result res = ma_sound_init_from_file(engine, sample->filename.c_str(), flags, NULL, NULL, voice);
	if (res != MA_SUCCESS)
	{
		debug << "AudioSystem: could not open " << sample->filename << ": " << ma_result_description(res) << endl;
		delete voice;
		return NULL;
	}

	ma_sound_set_volume(voice, sample->volume);
	return voice;
}

Sample *AudioSystem::CreateSample(const std::string &filename, float volume, bool stream)
{
	Sample *sample = new Sample();
	sample->filename = filename;
	sample->streamed = stream;
	sample->volume = volume;
	sample->owner = this;
	live.insert(sample);

	//silent mode: the sample exists but has no voice
	if (engine == NULL) return sample;

	sample->sound = CreateVoice(sample);
	if (sample->sound == NULL)
	{
		delete sample;	//destructor calls Forget()
		return NULL;
	}
	return sample;
}

void AudioSystem::Forget(Sample *sample)
{
	live.erase(sample);

	SampleIterator i = samples.begin();
	while (i != samples.end())
	{
		if ((*i) == sample) i = samples.erase(i);
		else ++i;
	}
}

Sample* AudioSystem::Load(std::string filename, float volume)
{
	if (filename.length() == 0) return NULL;

	Sample *sample = CreateSample(filename, volume, false);
	if (sample == NULL)
		debug << "AudioSystem::Load: Could not load " << filename << endl;
	return sample;
}

bool AudioSystem::Load(std::string filename, std::string name, float volume)
{
	if (filename.length() == 0 || name.length() == 0) return false;

	Sample *sample = CreateSample(filename, volume, false);
	if (sample == NULL)
	{
		debug << "AudioSystem::Load: Could not load " << filename << ", string " << name << endl;
		return false;
	}

	sample->setName(name);
	samples.push_back(sample);
	return true;
}

Sample* AudioSystem::LoadMusic(std::string filename, float volume)
{
	if (filename.length() == 0) return NULL;

	Sample *sample = CreateSample(filename, volume, true);
	if (sample == NULL)
		debug << "AudioSystem::LoadMusic: Could not load " << filename << endl;
	return sample;
}

bool AudioSystem::LoadMusic(std::string filename, std::string name, float volume)
{
	if (filename.length() == 0 || name.length() == 0) return false;

	Sample *sample = CreateSample(filename, volume, true);
	if (sample == NULL)
	{
		debug << "AudioSystem::LoadMusic: Could not load " << filename << ", string " << name << endl;
		return false;
	}

	sample->setName(name);
	samples.push_back(sample);
	return true;
}

bool AudioSystem::SampleExists(std::string name)
{
	return FindSample(name) != NULL;
}

bool AudioSystem::IsPlaying(std::string name)
{
	return IsPlaying(FindSample(name));
}

bool AudioSystem::IsPlaying(Sample *sample)
{
	if (sample == NULL || sample->sound == NULL) return false;

	if (ma_sound_is_playing(sample->sound)) return true;
	for (size_t i = 0; i < sample->extraVoices.size(); ++i)
		if (ma_sound_is_playing(sample->extraVoices[i])) return true;

	return false;
}

Sample *AudioSystem::FindSample(std::string name)
{
	for (SampleIterator i = samples.begin(); i != samples.end(); ++i)
	{
		if ((*i)->getName() == name)
			return (*i);
	}
	return NULL;
}

bool AudioSystem::Play(std::string name, bool doLoop)
{
	//prevent playback based on global setting
	if (!bPlay) return true;

	Sample *sample = FindSample(name);
	if (sample == NULL)
	{
		debug << "AudioSystem::Play: Could not play " << name << ": no such sample" << endl;
		return false;
	}

	return Play(sample, doLoop);
}

bool AudioSystem::Play(Sample *sample, bool doLoop)
{
	//prevent playback based on global setting
	if (!bPlay) return true;

	if (sample == NULL)
	{
		debug << "AudioSystem::Play: Cannot play NULL sample" << endl;
		return false;
	}

	//silent mode
	if (engine == NULL) return true;
	if (sample->sound == NULL) return false;

	//FMOD started each play on a free channel, so a one-shot effect could
	//overlap itself; do the same with an extra voice
	if (!doLoop && !sample->loop && ma_sound_is_playing(sample->sound))
	{
		ma_sound *voice = CreateVoice(sample);
		if (voice != NULL)
		{
			ma_sound_set_looping(voice, MA_FALSE);
			if (ma_sound_start(voice) == MA_SUCCESS)
			{
				sample->extraVoices.push_back(voice);
				return true;
			}
			ma_sound_uninit(voice);
			delete voice;
		}
		//otherwise fall through and restart the primary voice
	}

	ma_sound_stop(sample->sound);
	ma_sound_seek_to_pcm_frame(sample->sound, 0);
	sample->SetLoop(doLoop);
	sample->paused = false;

	ma_result res = ma_sound_start(sample->sound);
	if (res != MA_SUCCESS)
	{
		debug << "AudioSystem::Play: Could not play " << sample->filename << ": " << ma_result_description(res) << endl;
		return false;
	}
	return true;
}

bool AudioSystem::PlayMusic(std::string name, bool doLoop)
{
	return Play(name, doLoop);
}

bool AudioSystem::PlayMusic(Sample *sample, bool doLoop)
{
	return Play(sample, doLoop);
}

void AudioSystem::PauseMusic(std::string name)
{
	Sample *sample = FindSample(name);
	if (sample == NULL)
	{
		debug << "AudioSystem::PauseMusic: Could not pause " << name << endl;
		return;
	}
	sample->SetPaused(true);
}

void AudioSystem::UnpauseMusic(std::string name)
{
	Sample *sample = FindSample(name);
	if (sample == NULL)
	{
		debug << "AudioSystem::UnpauseMusic: Could not unpause " << name << endl;
		return;
	}
	sample->SetPaused(false);
}

void AudioSystem::Stop(std::string name)
{
	Stop(FindSample(name));
}

void AudioSystem::Stop(Sample *sample)
{
	if (sample == NULL) return;

	for (size_t i = 0; i < sample->extraVoices.size(); ++i)
	{
		ma_sound_uninit(sample->extraVoices[i]);
		delete sample->extraVoices[i];
	}
	sample->extraVoices.clear();

	if (sample->sound != NULL)
	{
		ma_sound_stop(sample->sound);
		ma_sound_seek_to_pcm_frame(sample->sound, 0);
	}
	sample->paused = false;
}

void AudioSystem::StopAll()
{
	for (SampleIterator i = samples.begin(); i != samples.end(); ++i)
		Stop(*i);
}

void AudioSystem::StopAllExcept(std::string name)
{
	for (SampleIterator i = samples.begin(); i != samples.end(); ++i)
	{
		if ((*i)->getName() != name)
			Stop(*i);
	}
}

void AudioSystem::Delete(std::string name)
{
	//pull the matches out first; deleting a Sample edits this vector
	std::vector<Sample*> doomed;
	SampleIterator i = samples.begin();
	while (i != samples.end())
	{
		if ((*i)->getName() == name)
		{
			doomed.push_back(*i);
			i = samples.erase(i);
		}
		else ++i;
	}

	for (size_t n = 0; n < doomed.size(); ++n)
	{
		Stop(doomed[n]);
		delete doomed[n];
	}
}
