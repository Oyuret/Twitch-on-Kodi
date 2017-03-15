# -*- coding: utf-8 -*-
"""
     
    Copyright (C) 2016 Twitch-on-Kodi
    
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import json
from functools import wraps
import utils
from common import kodi, log_utils
from constants import Keys
from twitch import queries as twitch_queries
from twitch import oauth
from twitch.api import v5 as twitch
from twitch.api import usher
from twitch.exceptions import ResourceUnavailableException

i18n = utils.i18n


def api_error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            try:
                logging_result = json.dumps(result, indent=4)
            except:
                logging_result = result
            log_utils.log(logging_result, log_utils.LOGDEBUG)
            try:
                if 'error' in result:
                    message = '[Status {0}] {1}'.format(result['status'], result['message'])
                    log_utils.log('Error |{0}| message |{1}|'.format(result['error'], message), log_utils.LOGERROR)
                    kodi.notify('{0} ({1})'.format(i18n('error'), result['error']), message, duration=7000, sound=False)
                    sys.exit(0)
            except:
                pass
            if not result or (isinstance(result, dict) and ('_total' in result) and (int(result['_total'] == 0))):
                kodi.notify(msg=i18n('no_results_returned'), duration=5000, sound=False)
            return result
        except ResourceUnavailableException as error:
            log_utils.log('Error: Resource not available |{0}|'.format(error.message), log_utils.LOGERROR)
            kodi.notify(i18n('error'), error.message, duration=7000, sound=False)
            sys.exit(0)

    return wrapper


class Twitch:
    api = twitch
    usher = usher
    queries = twitch_queries
    client_id = utils.get_client_id()
    access_token = utils.get_oauth_token(token_only=True, required=False)

    def __init__(self):
        self.queries.CLIENT_ID = self.client_id
        self.queries.OAUTH_TOKEN = self.access_token
        self.client = oauth.MobileClient(self.client_id)

    @api_error_handler
    @utils.cache.cache_function(cache_limit=1)
    def get_user(self):
        return self.api.users.user()

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_featured_streams(self):
        return self.api.streams.featured()

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_top_games(self, offset, limit):
        return self.api.games.top(offset=offset, limit=limit)

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_all_channels(self, offset, limit):
        return self.api.streams.all(offset=offset, limit=limit)

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_all_teams(self, offset, limit):
        return self.api.teams.active(offset=offset, limit=limit)

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_followed_channels(self, identification, offset, limit):
        return self.api.follows.by_id(identification=identification, limit=limit, offset=offset)

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_channel_videos(self, channel_id, offset, limit, broadcast_type):
        return self.api.videos.by_channel(identification=channel_id, limit=limit, offset=offset, broadcast_type=broadcast_type)

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_game_streams(self, game, offset, limit):
        return self.api.streams.all(game=game, limit=limit, offset=offset)

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_channel_search(self, query, offset, limit):
        return self.api.search.channels(query=query, limit=limit, offset=offset)

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_stream_search(self, query, offset, limit):
        return self.api.search.streams(query=query, limit=limit, offset=offset)

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_game_search(self, query):
        return self.api.search.games(query=query)

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_video_by_id(self, video_id):
        return self.api.videos.by_id(identification=video_id)

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_channel_stream(self, name):
        return self.api.streams.all(channel=name)

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_streams_by_channels(self, names, offset, limit):
        query = self.queries.ApiQuery('streams')
        query.add_param('offset', offset)
        query.add_param('limit', limit)
        query.add_param('channel', names)
        return query.execute()

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_followed_games(self, name):
        query = self.queries.HiddenApiQuery('users/{0}/follows/games'.format(name))
        return query.execute()

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_vod(self, video_id):
        return self.usher.video(video_id)

    @api_error_handler
    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_live(self, name):
        return self.usher.live(name)

    @utils.cache.cache_function(cache_limit=utils.cache_limit)
    def get_following_streams(self, user_id):
        following_channels = self._get_followed_channels(user_id)
        channels = sorted(following_channels, key=lambda k: k[Keys.DISPLAY_NAME].lower())
        channel_names = ','.join([channel[Keys.NAME] for channel in channels])
        live = []
        limit = 100
        offset = 0

        while True:
            temp = self.get_streams_by_channels(channel_names, offset, limit)
            if len(temp[Keys.STREAMS]) == 0:
                break
            for stream in temp[Keys.STREAMS]:
                live.append(stream)
            offset += limit
            if temp[Keys.TOTAL] <= offset:
                break

        channels = {Keys.LIVE: live, Keys.OTHERS: channels}
        return channels

    @staticmethod
    def get_video_for_quality(videos, source=True):
        qualities = []
        for quality in videos:
            if source and 'source' in quality.lower():
                    return videos[quality]
            qualities.append(quality)

        result = kodi.Dialog().select(i18n('play_choose_quality'), [quality for quality in qualities])
        if result == -1:
            return None
        else:
            return videos[qualities[result]]

    def _get_followed_channels(self, username):
        acc = []
        limit = 100
        offset = 0
        while True:
            temp = self.get_followed_channels(username, offset, limit)
            if len(temp[Keys.FOLLOWS]) == 0:
                break
            for channel in temp[Keys.FOLLOWS]:
                acc.append(channel[Keys.CHANNEL])
            offset += limit
            if temp[Keys.TOTAL] <= offset:
                break

        return acc
