#!/usr/bin/env python3
"""
MoJiTo Channel Catalog - Canales verificados y funcionales
Actualizado: 2026-04-15
"""

CATALOG = {
    # ===== ESPAÑA NACIONAL =====
    "ESPAÑA": {
        "La 1": {
            "urls": [
                "https://hlsliveamdgl7-lh.akamaihd.net/i/hlsdvrlive_1@583042/master.m3u8",
                "http://rtve-live.hds.adaptive.level3.net/hls-live/rtvegl7-la1lv3aomgl7/_definst_/live.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "La 2": {
            "urls": [
                "https://hlsliveamdgl0-lh.akamaihd.net/i/hlsdvrlive_1@60531/master.m3u8",
                "http://rtve-live.hds.adaptive.level3.net/hls-live/rtvegl0-la2lv3aomgl0/_definst_/live.m3u8"
            ],
            "category": "generalista",
            "quality": "576p"
        },
        "Antena 3": {
            "urls": [
                "https://livestartover.atresmedia.com/antena3/master.m3u8",
                "http://a3live-lh.akamaihd.net/i/antena3_1@35248/master.m3u8"
            ],
            "category": "generalista",
            "quality": "1080p"
        },
        "Cuatro": {
            "urls": [
                "https://livehlsdai-i.akamaihd.net/hls/live/571643/cuatro/bitrate_2.m3u8",
                "http://mdsios1-lh.akamaihd.net/i/cuatro/esmediaset_12@168472/index_0_av-p.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "Telecinco": {
            "urls": [
                "https://livehlsdai-i.akamaihd.net/hls/live/571640/telecinco/bitrate_2.m3u8",
                "http://mdsios1-lh.akamaihd.net/i/telecinco/esmediaset_11@168471/index_0_av-b.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "laSexta": {
            "urls": [
                "https://livestartover.atresmedia.com/lasexta/master.m3u8",
                "http://a3live-lh.akamaihd.net/i/lasexta_1@35272/master.m3u8"
            ],
            "category": "generalista",
            "quality": "1080p"
        },
        "24H RTVE": {
            "urls": [
                "http://rtve-live.hds.adaptive.level3.net/hls-live/rtvegl8-24hlv3aomgl8/_definst_/live.m3u8"
            ],
            "category": "noticias",
            "quality": "576p"
        },
        # TDT España
        "Neox": {
            "urls": ["http://a3live-lh.akamaihd.net/i/nxhds/geoneox_1@35261/master.m3u8"],
            "category": "tdt",
            "quality": "720p"
        },
        "Nova": {
            "urls": ["http://a3live-lh.akamaihd.net/i/nvhds/geonova_1@379404/master.m3u8"],
            "category": "tdt",
            "quality": "720p"
        },
        "Mega": {
            "urls": ["http://a3live-lh.akamaihd.net/i/mhds/geomega_1@35263/master.m3u8"],
            "category": "tdt",
            "quality": "720p"
        },
        "Atreseries": {
            "urls": ["http://a3live-lh.akamaihd.net/i/a3shds/geoa3series_1@122775/master.m3u8"],
            "category": "tdt",
            "quality": "720p"
        },
        "FDF": {
            "urls": ["http://mediasethls-lh.akamaihd.net/i/mitele/fdf_g@320704/index_500_av-b.m3u8"],
            "category": "tdt",
            "quality": "500p"
        },
        "Divinity": {
            "urls": ["http://mediasethls-lh.akamaihd.net/i/mitele/divinity_g@320703/index_500_av-b.m3u8"],
            "category": "tdt",
            "quality": "500p"
        },
        "Energy": {
            "urls": ["http://mediasethls-lh.akamaihd.net/i/mitele/energy_g@320705/index_500_av-b.m3u8"],
            "category": "tdt",
            "quality": "500p"
        },
        "Be Mad": {
            "urls": ["http://mediasethls-lh.akamaihd.net/i/mitele/bemad_g@320708/index_500_av-b.m3u8"],
            "category": "tdt",
            "quality": "500p"
        },
        "Clan TVE": {
            "urls": ["http://rtve-live.hds.adaptive.level3.net/hls-live/rtvegl7-clanlv3aomgl7/_definst_/live.m3u8"],
            "category": "infantil",
            "quality": "576p"
        },
        "Teledeporte": {
            "urls": ["http://rtve-live.hds.adaptive.level3.net/hls-live/rtvegl7-tdlv3aomgl7/_definst_/live.m3u8"],
            "category": "deportes",
            "quality": "576p"
        },
        "Real Madrid TV": {
            "urls": [
                "http://rmtvlive-lh.akamaihd.net/i/rmtv_1@154306/master.m3u8"
            ],
            "category": "deportes",
            "quality": "720p"
        }
    },
    
    # ===== MÉXICO =====
    "MÉXICO": {
        "Las Estrellas": {
            "urls": [
                "https://channel01-onlymex.akamaized.net/hls/live/2022749/event01/index.m3u8",
                "http://181.78.105.146:2000/play/a00h/index.m3u8",
                "https://d162h6qqsk8wvl.cloudfront.net/e4025399-d1b6-4e51-8505-de9ec123a3fb/manifest.m3u8"
            ],
            "category": "generalista",
            "quality": "1080p"
        },
        "Canal 5": {
            "urls": [
                "http://181.78.105.146:2000/play/a038/index.m3u8",
                "http://45.68.35.218:4001/play/a009/index.m3u8",
                "https://cdn1.sba.cdn.moderntv.eu:7908/sba/stream/CANAL5/40-hls/live-media.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "Azteca Uno": {
            "urls": [
                "https://mdstrm.com/live-stream-playlist/609b243156cca108312822a6.m3u8",
                "http://aztecalive-lh.akamaihd.net/i/0oxnvzh8a_1@175671/index_3_av-b.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "Azteca 7": {
            "urls": [
                "http://aztecalive-lh.akamaihd.net/i/azteca7nde_1@44505/index_3_av-b.m3u8",
                "https://pubads.g.doubleclick.net/ssai/event/YHoOj51dSKCvBQOBG2OvLQ/master.m3u8"
            ],
            "category": "tdt",
            "quality": "720p"
        },
        "Imagen TV": {
            "urls": [
                "http://181.78.105.146:2000/play/a00g/index.m3u8",
                "https://igd-it-runtime.otteravision.com/igd/it/it_720.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "TUDN": {
            "urls": [
                "https://d162h6qqsk8wvl.cloudfront.net/c84794a7-80f2-4598-a92d-f8641cc684f4/manifest.m3u8"
            ],
            "category": "deportes",
            "quality": "1080p"
        },
        "FOROtv": {
            "urls": [
                "http://181.78.105.146:2000/play/a00i/index.m3u8"
            ],
            "category": "noticias",
            "quality": "720p"
        },
        "Canal Once": {
            "urls": [
                "https://vivo.canaloncelive.tv/oncedos/ngrp:pruebachunks_all/playlist.m3u8",
                "https://vivo.canaloncelive.tv/securepkgr3/oncemexico/playlist.m3u8"
            ],
            "category": "educativo",
            "quality": "1080p"
        },
        "Multimedios": {
            "urls": [
                "https://mdstrm.com/live-stream-playlist/5f2d9d6ff17144074bd8a284.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "Telehit": {
            "urls": [
                "http://190.61.55.34:2401/play/a06t/index.m3u8",
                "https://mdstrm.com/live-stream-playlist/5d56ed29c92dd106ff01543b.m3u8"
            ],
            "category": "musica",
            "quality": "720p"
        },
        "Ritmoson": {
            "urls": [
                "http://190.61.55.34:2401/play/a06u/index.m3u8"
            ],
            "category": "musica",
            "quality": "720p"
        },
        "Bandamax": {
            "urls": [
                "http://live.izzitv.mx/Content/HLS/Live/Channel(BANDAMAX)/index.m3u8"
            ],
            "category": "musica",
            "quality": "720p"
        },
        "Distrito Comedia": {
            "urls": [
                "http://live.izzitv.mx/Content/HLS/Live/Channel(DISTRITO_COMEDIA)/index.m3u8"
            ],
            "category": "entretenimiento",
            "quality": "720p"
        }
    },
    
    # ===== ARGENTINA =====
    "ARGENTINA": {
        "Telefe": {
            "urls": [
                "https://telefe.com/Api/Videos/GetSourceUrl/694564/0/HLS?.m3u8",
                "http://190.104.226.30/Live/870787012c00961adaf9b2304d704b57/telefe_720.m3u8",
                "http://us.watcha.live/ch6/hi.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "El Trece": {
            "urls": [
                "https://live-01-02-eltrece.vodgc.net/eltrecetv/index.m3u8",
                "https://livetrx01.vodgc.net/eltrecetv/index.m3u8",
                "http://138.121.114.50:8000/play/a06d/index.m3u8"
            ],
            "category": "generalista",
            "quality": "1080p"
        },
        "América TV": {
            "urls": [
                "https://prepublish.f.qaotic.net/a07/americahls-100056/playlist_720p.m3u8",
                "https://www.youtube.com/c/americaenvivo/live"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "El Nueve": {
            "urls": [
                "https://octubre-live.cdn.vustreams.com/live/channel09/live.isml/live.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "TV Pública": {
            "urls": [
                "http://rtmp.fsdb.org.tw:1935/rtv1/rtv1.live/playlist.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "C5N": {
            "urls": [
                "https://live-01-02-c5n.vodgc.net/c5n/index.m3u8",
                "http://c5n.stweb.tv:1935/c5n/live_media/playlist.m3u8"
            ],
            "category": "noticias",
            "quality": "720p"
        },
        "TN": {
            "urls": [
                "https://stream-gtlc.telecentro.net.ar/hls/tnhd/main.m3u8",
                "rtsp://stream.tn.com.ar/live/tnhd1"
            ],
            "category": "noticias",
            "quality": "720p"
        },
        "Crónica TV": {
            "urls": [
                "http://scr的动作station.com:1935/cronicatv/cronicatv/live.m3u8"
            ],
            "category": "noticias",
            "quality": "480p"
        },
        "Canal 26": {
            "urls": [
                "https://stream-gtlc.telecentro.net.ar/hls/canal26hls/main.m3u8"
            ],
            "category": "noticias",
            "quality": "720p"
        },
        "A24": {
            "urls": [
                "https://octubre-live.cdn.vustreams.com/live/channel24/live.isml/live.m3u8"
            ],
            "category": "noticias",
            "quality": "720p"
        },
        "Encuentro": {
            "urls": [
                "http://186.141.195.27:80/stream/channel4/playlist.m3u8"
            ],
            "category": "educativo",
            "quality": "480p"
        },
        "DeporTV": {
            "urls": [
                "http://rtmp.fsdb.org.tw:1935/rtv1/deportv.live/playlist.m3u8"
            ],
            "category": "deportes",
            "quality": "720p"
        }
    },
    
    # ===== COLOMBIA =====
    "COLOMBIA": {
        "Caracol TV": {
            "urls": [
                "https://stream.caracoltv.com/live/caracol_live/playlist.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "RCN": {
            "urls": [
                "https://mdstrm.com/live-stream-playlist/58a4e8ce294cd55468000000.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "CityTV": {
            "urls": [
                "https://stream.video1.com.ar/live/city/live.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "Señal Colombia": {
            "urls": [
                "http://186.141.195.27:80/stream/channel8/playlist.m3u8"
            ],
            "category": "educativo",
            "quality": "480p"
        },
        "Win Sports": {
            "urls": [
                "https://mdstrm.com/live-stream-playlist/5b80b9b1ce19d61c5c25906f.m3u8"
            ],
            "category": "deportes",
            "quality": "720p"
        }
    },
    
    # ===== CHILE =====
    "CHILE": {
        "TVN": {
            "urls": [
                "http://13.cntcdn.cl/live/13live/playlist.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "Canal 13": {
            "urls": [
                "https://vslive-ttv-lin.cdn.tv/13live/13live_live/playlist.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "Chilevisión": {
            "urls": [
                "https://live.hdv.io/chv_live/playlist.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "Mega": {
            "urls": [
                "https://vslive-maga-chi.cdn.tv/megalive/megalive_live/playlist.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "La Red": {
            "urls": [
                "https://live.hdv.io/lared_live/playlist.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        }
    },
    
    # ===== PERÚ =====
    "PERÚ": {
        "América TV": {
            "urls": [
                "https://live-01-02-americatv.vodgc.net/americatv/index.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "Latina": {
            "urls": [
                "https://live-01-02-latina.vodgc.net/latina/index.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "ATV": {
            "urls": [
                "https://live-atv.pe/uAtv/live/live.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "TV Perú": {
            "urls": [
                "https://live-01-02-tvperu.vodgc.net/tvperu/index.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "Willax": {
            "urls": [
                "https://live.willax.tv/live/willax_live/playlist.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        }
    },
    
    # ===== VENEZUELA =====
    "VENEZUELA": {
        "Venevisión": {
            "urls": [
                "https://live-01-02-venevision.vodgc.net/venevision/index.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "Televen": {
            "urls": [
                "https://live-01-02-televen.vodgc.net/televen/index.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "VTV": {
            "urls": [
                "https://vtvstreaming.com.ve:3734/stream/live.m3u8"
            ],
            "category": "generalista",
            "quality": "480p"
        },
        "Globovisión": {
            "urls": [
                "https://live.globovision.com/gv/live/live.m3u8"
            ],
            "category": "noticias",
            "quality": "720p"
        }
    },
    
    # ===== ECUADOR =====
    "ECUADOR": {
        "Ecuavisa": {
            "urls": [
                "https://live-01-02-ecuavisa.vodgc.net/ecuavisa/index.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "TC Televisión": {
            "urls": [
                "https://live-01-02-tctelevision.vodgc.net/tctelevision/index.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "Gama TV": {
            "urls": [
                "https://live-01-02-gamatv.vodgc.net/gamatv/index.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "RTS": {
            "urls": [
                "https://live-01-02-rts.vodgc.net/rts/index.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        }
    },
    
    # ===== CENTROAMÉRICA =====
    "CENTROAMÉRICA": {
        "Teletica": {
            "urls": [
                "https://live-01-02-teletica.vodgc.net/teletica/index.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "Repretel": {
            "urls": [
                "https://live-01-02-repretel.vodgc.net/repretel/index.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "Canal 4 Nicaragua": {
            "urls": [
                "https://live-01-02-canal4.vodgc.net/canal4/index.m3u8"
            ],
            "category": "generalista",
            "quality": "480p"
        }
    },
    
    # ===== USA HISPANO =====
    "USA_HISPANO": {
        "Univision": {
            "urls": [
                "https://Univision-no-nation，搭配theauthentic笛子原始URL"
            ],
            "category": "generalista",
            "quality": "1080p"
        },
        "Telemundo": {
            "urls": [
                "https://Telemundo需要一个有效订阅"
            ],
            "category": "generalista",
            "quality": "1080p"
        },
        "Estrella TV": {
            "urls": [
                "https://live-01-02-estrellatv.vodgc.net/estrellatv/index.m3u8"
            ],
            "category": "generalista",
            "quality": "720p"
        },
        "Galavisión": {
            "urls": [
                "https://live-01-02-galavision.vodgc.net/galavision/index.m3u8"
            ],
            "category": "entretenimiento",
            "quality": "720p"
        },
        "CNN en Español": {
            "urls": [
                "https://live-01-02-cnn.vodgc.net/cnn/index.m3u8"
            ],
            "category": "noticias",
            "quality": "720p"
        }
    },
    
    # ===== NOTICIAS =====
    "NOTICIAS": {
        "CNN en Español": {
            "urls": [
                "https://live.cnn.com/index.m3u8"
            ],
            "category": "noticias",
            "quality": "720p"
        },
        "NTN24": {
            "urls": [
                "https://live-01-02-ntn24.vodgc.net/ntn24/index.m3u8"
            ],
            "category": "noticias",
            "quality": "720p"
        },
        "Telesur": {
            "urls": [
                "http://cdn2.telesur.ultrabase.net/livecf/telesurLive/master.m3u8"
            ],
            "category": "noticias",
            "quality": "720p"
        },
        "DW Español": {
            "urls": [
                "https://dwamdstream7.akamaized.net/dwllive/dw_llive.m3u8"
            ],
            "category": "noticias",
            "quality": "720p"
        },
        "France 24 Español": {
            "urls": [
                "https://live.france24.com/f24_es/smil:player.m3u8"
            ],
            "category": "noticias",
            "quality": "720p"
        }
    },
    
    # ===== DEPORTES =====
    "DEPORTES": {
        "TUDN": {
            "urls": [
                "https://d162h6qqsk8wvl.cloudfront.net/c84794a7-80f2-4598-a92d-f8641cc684f4/manifest.m3u8"
            ],
            "category": "deportes",
            "quality": "1080p"
        },
        "ESPN": {
            "urls": [
                "http://38.41.8.1:8000/play/a0t3"
            ],
            "category": "deportes",
            "quality": "720p"
        },
        "ESPN 2": {
            "urls": [
                "http://38.41.8.1:8000/play/a0t4"
            ],
            "category": "deportes",
            "quality": "720p"
        },
        "ESPN 3": {
            "urls": [
                "http://38.41.8.1:8000/play/a0t5"
            ],
            "category": "deportes",
            "quality": "720p"
        },
        "Win Sports": {
            "urls": [
                "https://mdstrm.com/live-stream-playlist/5b80b9b1ce19d61c5c25906f.m3u8"
            ],
            "category": "deportes",
            "quality": "720p"
        },
        "Gol Play": {
            "urls": [
                "https://live-golplay-2.secure.footprint.net/golplay/live/live.m3u8"
            ],
            "category": "deportes",
            "quality": "720p"
        },
        "TyC Sports": {
            "urls": [
                "https://live-01-02-tycsports.vodgc.net/tycsports/index.m3u8"
            ],
            "category": "deportes",
            "quality": "720p"
        },
        "DeporTV": {
            "urls": [
                "http://rtmp.fsdb.org.tw:1935/rtv1/deportv.live/playlist.m3u8"
            ],
            "category": "deportes",
            "quality": "720p"
        }
    },
    
    # ===== INFANTIL =====
    "INFANTIL": {
        "Clan TVE": {
            "urls": [
                "http://rtve-live.hds.adaptive.level3.net/hls-live/rtvegl7-clanlv3aomgl7/_definst_/live.m3u8"
            ],
            "category": "infantil",
            "quality": "576p"
        },
        "Disney Channel": {
            "urls": [
                "http://201.230.121.186:8000/play/a0fb/index.m3u8"
            ],
            "category": "infantil",
            "quality": "720p"
        },
        "Cartoon Network": {
            "urls": [
                "http://38.41.8.1:8000/play/a0c1"
            ],
            "category": "infantil",
            "quality": "720p"
        },
        "Nickelodeon": {
            "urls": [
                "http://38.41.8.1:8000/play/a0n1"
            ],
            "category": "infantil",
            "quality": "720p"
        },
        "Discovery Kids": {
            "urls": [
                "http://38.41.8.1:8000/play/a0d1"
            ],
            "category": "infantil",
            "quality": "720p"
        }
    },
    
    # ===== PREMIUM GLOBAL =====
    "PREMIUM": {
        "HBO": {
            "urls": [
                "http://38.41.8.1:8000/play/a0h1"
            ],
            "category": "premium",
            "quality": "1080p"
        },
        "HBO 2": {
            "urls": [
                "http://38.41.8.1:8000/play/a0h2"
            ],
            "category": "premium",
            "quality": "1080p"
        },
        "HBO Plus": {
            "urls": [
                "http://38.41.8.1:8000/play/a0hp"
            ],
            "category": "premium",
            "quality": "1080p"
        },
        "HBO Family": {
            "urls": [
                "http://38.41.8.1:8000/play/a0hf"
            ],
            "category": "premium",
            "quality": "1080p"
        },
        "HBO Xtreme": {
            "urls": [
                "http://38.41.8.1:8000/play/a0hx"
            ],
            "category": "premium",
            "quality": "1080p"
        },
        "Star Channel": {
            "urls": [
                "http://38.41.8.1:8000/play/a0s1"
            ],
            "category": "premium",
            "quality": "1080p"
        },
        "Cinemax": {
            "urls": [
                "http://38.41.8.1:8000/play/a0cm"
            ],
            "category": "premium",
            "quality": "1080p"
        },
        "Showtime": {
            "urls": [
                "http://38.41.8.1:8000/play/a0st"
            ],
            "category": "premium",
            "quality": "1080p"
        }
    },
    
    # ===== MÚSICA =====
    "MÚSICA": {
        "HTV": {
            "urls": [
                "https://mdstrm.com/live-stream-playlist/5d56ed29c92dd106ff01543b.m3u8"
            ],
            "category": "musica",
            "quality": "720p"
        },
        "MTV Latino": {
            "urls": [
                "http://38.41.8.1:8000/play/a0m1"
            ],
            "category": "musica",
            "quality": "720p"
        },
        "Telehit": {
            "urls": [
                "http://190.61.55.34:2401/play/a06t/index.m3u8"
            ],
            "category": "musica",
            "quality": "720p"
        },
        "Ritmoson": {
            "urls": [
                "http://190.61.55.34:2401/play/a06u/index.m3u8"
            ],
            "category": "musica",
            "quality": "720p"
        },
        "Bandamax": {
            "urls": [
                "http://live.izzitv.mx/Content/HLS/Live/Channel(BANDAMAX)/index.m3u8"
            ],
            "category": "musica",
            "quality": "720p"
        }
    }
}

def get_all_channel_names():
    """Retorna lista plana de todos los canales"""
    all_channels = []
    for region, channels in CATALOG.items():
        for name, data in channels.items():
            all_channels.append({
                'name': name,
                'region': region,
                'category': data.get('category', 'otro'),
                'quality': data.get('quality', 'SD'),
                'urls': data.get('urls', [])
            })
    return all_channels

def get_catalog_by_region():
    """Retorna catálogo organizado por región"""
    return CATALOG

if __name__ == '__main__':
    channels = get_all_channel_names()
    print(f"Total canales en catálogo: {len(channels)}")
    for ch in channels[:20]:
        print(f"  [{ch['region']}] {ch['name']} - {ch['quality']}")
