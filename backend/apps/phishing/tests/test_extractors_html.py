from __future__ import annotations

import requests
import responses as responses_lib
from bs4 import BeautifulSoup

import pytest

from apps.phishing.extractors.html_ext import HtmlExtractor

BASE = "example.com"


@pytest.fixture
def ext() -> HtmlExtractor:
    return HtmlExtractor()


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


# ══════════════════════════════════════════════════════════════════════════════
# feature_names / helpers
# ══════════════════════════════════════════════════════════════════════════════

def test_feature_names_contract(ext):
    assert ext.feature_names == [
        "request_url", "url_of_anchor", "links_in_tags", "sfh",
        "submitting_to_email", "redirect", "on_mouseover", "rightclick",
        "popupwindow", "iframe", "favicon",
    ]


def test_registered_domain(ext):
    assert ext._registered_domain("https://sub.example.com/path") == "example.com"
    assert ext._registered_domain("http://evil.co.uk/") == "evil.co.uk"
    assert ext._registered_domain("not-a-url") == ""


def test_is_external_same_domain(ext):
    assert ext._is_external("https://example.com/img.png", "example.com") is False


def test_is_external_different_domain(ext):
    assert ext._is_external("https://evil.com/img.png", "example.com") is True


def test_is_external_relative_url(ext):
    assert ext._is_external("/img.png", "example.com") is None


def test_is_external_non_http_scheme(ext):
    assert ext._is_external("ftp://example.com/f", "example.com") is None


# ══════════════════════════════════════════════════════════════════════════════
# Level 1 — compute-method unit tests (no HTTP)
# ══════════════════════════════════════════════════════════════════════════════

# ── request_url ───────────────────────────────────────────────────────────────

def test_compute_request_url_all_internal(ext):
    soup = _soup('<img src="https://example.com/a.png"><img src="https://example.com/b.png">')
    assert ext._compute_request_url(soup, BASE) == 1


def test_compute_request_url_all_external(ext):
    soup = _soup('<img src="https://cdn.evil.com/a.png"><img src="https://other.com/b.png">')
    assert ext._compute_request_url(soup, BASE) == -1


def test_compute_request_url_no_tags(ext):
    soup = _soup("<p>text</p>")
    assert ext._compute_request_url(soup, BASE) == 1


def test_compute_request_url_mixed_suspicious(ext):
    # 2 external, 2 internal → 50% → 0 (22-61%)
    soup = _soup(
        '<img src="https://evil.com/a.png">'
        '<img src="https://evil.com/b.png">'
        '<img src="https://example.com/c.png">'
        '<img src="https://example.com/d.png">'
    )
    assert ext._compute_request_url(soup, BASE) == 0


# ── url_of_anchor ─────────────────────────────────────────────────────────────

def test_compute_url_of_anchor_all_external(ext):
    soup = _soup(
        '<a href="https://other.com/1">A</a>'
        '<a href="https://other.com/2">B</a>'
        '<a href="https://other.com/3">C</a>'
    )
    assert ext._compute_url_of_anchor(soup, BASE) == -1


def test_compute_url_of_anchor_mostly_internal(ext):
    soup = _soup(
        '<a href="https://example.com/1">A</a>'
        '<a href="https://example.com/2">B</a>'
        '<a href="https://example.com/3">C</a>'
        '<a href="https://other.com/x">X</a>'
    )
    # 1/4 = 25% → 1
    assert ext._compute_url_of_anchor(soup, BASE) == 1


def test_compute_url_of_anchor_relative_only(ext):
    # All relative → no absolute → return 1
    soup = _soup('<a href="/page">A</a><a href="#anchor">B</a>')
    assert ext._compute_url_of_anchor(soup, BASE) == 1


def test_compute_url_of_anchor_javascript_skipped(ext):
    soup = _soup(
        '<a href="javascript:void(0)">JS</a>'
        '<a href="https://example.com/">Home</a>'
    )
    # javascript: is skipped by _is_external, only absolute http counts
    assert ext._compute_url_of_anchor(soup, BASE) == 1


# ── links_in_tags ─────────────────────────────────────────────────────────────

def test_compute_links_in_tags_all_external(ext):
    soup = _soup(
        '<script src="https://evil.com/a.js"></script>'
        '<script src="https://evil.com/b.js"></script>'
        '<link href="https://evil.com/c.css">'
    )
    assert ext._compute_links_in_tags(soup, BASE) == -1


def test_compute_links_in_tags_all_internal(ext):
    soup = _soup(
        '<script src="https://example.com/a.js"></script>'
        '<link href="https://example.com/style.css">'
    )
    assert ext._compute_links_in_tags(soup, BASE) == 1


def test_compute_links_in_tags_no_tags(ext):
    soup = _soup("<p>text</p>")
    assert ext._compute_links_in_tags(soup, BASE) == 1


# ── sfh ──────────────────────────────────────────────────────────────────────

def test_compute_sfh_empty_action(ext):
    soup = _soup('<form action=""></form>')
    assert ext._compute_sfh(soup, BASE) == -1


def test_compute_sfh_hash_action(ext):
    soup = _soup('<form action="#"></form>')
    assert ext._compute_sfh(soup, BASE) == -1


def test_compute_sfh_about_blank(ext):
    soup = _soup('<form action="about:blank"></form>')
    assert ext._compute_sfh(soup, BASE) == -1


def test_compute_sfh_external_action(ext):
    soup = _soup('<form action="https://evil.com/steal"></form>')
    assert ext._compute_sfh(soup, BASE) == 0


def test_compute_sfh_same_domain_action(ext):
    soup = _soup('<form action="https://example.com/submit"></form>')
    assert ext._compute_sfh(soup, BASE) == 1


def test_compute_sfh_relative_action(ext):
    soup = _soup('<form action="/submit"></form>')
    assert ext._compute_sfh(soup, BASE) == 1


def test_compute_sfh_no_forms(ext):
    soup = _soup("<p>no form here</p>")
    assert ext._compute_sfh(soup, BASE) == 1


# ── submitting_to_email ───────────────────────────────────────────────────────

def test_compute_submitting_to_email_mailto(ext):
    soup = _soup('<form action="mailto:attacker@evil.com"></form>')
    assert ext._compute_submitting_to_email(soup) == -1


def test_compute_submitting_to_email_normal(ext):
    soup = _soup('<form action="/submit"></form>')
    assert ext._compute_submitting_to_email(soup) == 1


# ── redirect ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("count,expected", [
    (0, 1), (1, 1), (2, 1), (3, -1), (5, -1),
])
def test_compute_redirect(count, expected, ext):
    assert ext._compute_redirect(count) == expected


# ── on_mouseover ─────────────────────────────────────────────────────────────

def test_compute_on_mouseover_inline_attr(ext):
    soup = _soup('<a onmouseover="window.status=\'trick\'">x</a>')
    assert ext._compute_on_mouseover(soup) == -1


def test_compute_on_mouseover_script_window_status(ext):
    soup = _soup("<script>window.status='fake';</script>")
    assert ext._compute_on_mouseover(soup) == -1


def test_compute_on_mouseover_clean(ext):
    soup = _soup("<p>nothing here</p>")
    assert ext._compute_on_mouseover(soup) == 1


# ── rightclick ───────────────────────────────────────────────────────────────

def test_compute_rightclick_inline_oncontextmenu(ext):
    soup = _soup('<body oncontextmenu="return false;">')
    assert ext._compute_rightclick(soup) == -1


def test_compute_rightclick_event_button_2(ext):
    soup = _soup("<script>if(event.button==2){return false;}</script>")
    assert ext._compute_rightclick(soup) == -1


def test_compute_rightclick_event_button_strict_eq(ext):
    soup = _soup("<script>if(event.button === 2){return false;}</script>")
    assert ext._compute_rightclick(soup) == -1


def test_compute_rightclick_clean(ext):
    soup = _soup("<script>console.log('hello');</script>")
    assert ext._compute_rightclick(soup) == 1


# ── popupwindow ───────────────────────────────────────────────────────────────

def test_compute_popupwindow_found(ext):
    soup = _soup("<script>window.open('http://evil.com');</script>")
    assert ext._compute_popupwindow(soup) == -1


def test_compute_popupwindow_clean(ext):
    soup = _soup("<script>document.getElementById('x');</script>")
    assert ext._compute_popupwindow(soup) == 1


# ── iframe ────────────────────────────────────────────────────────────────────

def test_compute_iframe_found(ext):
    soup = _soup('<iframe src="https://evil.com/payload"></iframe>')
    assert ext._compute_iframe(soup) == -1


def test_compute_iframe_frameset(ext):
    soup = _soup('<frameset cols="50%,50%"><frame src="a.html"/></frameset>')
    assert ext._compute_iframe(soup) == -1


def test_compute_iframe_clean(ext):
    soup = _soup("<p>no frames</p>")
    assert ext._compute_iframe(soup) == 1


# ── favicon ───────────────────────────────────────────────────────────────────

def test_compute_favicon_same_domain_absolute(ext):
    soup = _soup('<link rel="icon" href="https://example.com/favicon.ico">')
    assert ext._compute_favicon(soup, BASE) == 1


def test_compute_favicon_external(ext):
    soup = _soup('<link rel="icon" href="https://evil.com/favicon.ico">')
    assert ext._compute_favicon(soup, BASE) == -1


def test_compute_favicon_relative(ext):
    soup = _soup('<link rel="icon" href="/favicon.ico">')
    assert ext._compute_favicon(soup, BASE) == 1


def test_compute_favicon_missing(ext):
    soup = _soup("<head><title>No icon</title></head>")
    assert ext._compute_favicon(soup, BASE) == 0


def test_compute_favicon_shortcut_icon(ext):
    soup = _soup('<link rel="shortcut icon" href="/icon.png">')
    assert ext._compute_favicon(soup, BASE) == 1


# ══════════════════════════════════════════════════════════════════════════════
# Level 2 — integration tests via responses library
# ══════════════════════════════════════════════════════════════════════════════

@responses_lib.activate
def test_full_extract_legitimate_site(ext):
    html = """<html>
        <head><link rel="icon" href="/favicon.ico"></head>
        <body>
            <img src="/logo.png"/>
            <a href="https://example.com/page">home</a>
            <form action="/submit"></form>
        </body></html>"""
    responses_lib.add(
        responses_lib.GET, "http://example.com/",
        body=html, status=200, content_type="text/html",
    )
    features = ext.extract("http://example.com/", {})
    assert features["request_url"] == 1
    assert features["url_of_anchor"] == 1
    assert features["favicon"] == 1
    assert features["iframe"] == 1
    assert features["sfh"] == 1
    assert features["submitting_to_email"] == 1
    assert features["redirect"] == 1


@responses_lib.activate
def test_full_extract_phishing_signals(ext):
    html = """<html><body>
        <img src="https://evil.com/track.gif"/>
        <img src="https://evil.com/pixel.gif"/>
        <a href="https://evil.com/steal">click</a>
        <form action="mailto:attacker@evil.com"></form>
        <iframe src="https://evil.com/payload"></iframe>
        <script>window.open('http://evil.com');</script>
    </body></html>"""
    responses_lib.add(
        responses_lib.GET, "http://example.com/",
        body=html, status=200, content_type="text/html",
    )
    features = ext.extract("http://example.com/", {})
    assert features["request_url"] == -1
    assert features["url_of_anchor"] == -1
    assert features["submitting_to_email"] == -1
    assert features["iframe"] == -1
    assert features["popupwindow"] == -1


@responses_lib.activate
def test_fetch_connection_error_returns_all_zero(ext):
    responses_lib.add(
        responses_lib.GET, "http://slow.example.com/",
        body=requests.exceptions.ConnectionError(),
    )
    features = ext.extract("http://slow.example.com/", {})
    assert all(v == 0 for v in features.values())


@responses_lib.activate
def test_redirect_count_tracked(ext):
    # 3 redirects → redirect == -1
    responses_lib.add(responses_lib.GET, "http://example.com/",
                      status=301, headers={"Location": "http://example.com/r1"})
    responses_lib.add(responses_lib.GET, "http://example.com/r1",
                      status=301, headers={"Location": "http://example.com/r2"})
    responses_lib.add(responses_lib.GET, "http://example.com/r2",
                      status=301, headers={"Location": "http://example.com/final"})
    responses_lib.add(responses_lib.GET, "http://example.com/final",
                      body="<html></html>", status=200)
    features = ext.extract("http://example.com/", {})
    assert features["redirect"] == -1
