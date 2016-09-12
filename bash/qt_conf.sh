#!/bin/bash
B=`pwd`
QT_DIR_NAME="qt5"
prefix=/usr
bindir=${prefix}/bin
libdir=${prefix}/lib
datadir=${prefix}/share
docdir=${datadir}/doc
includedir=${prefix}/include
sysconfdir=/etc/xdg
OE_QMAKE_PATH_HEADERS=${includedir}/${QT_DIR_NAME}
OE_QMAKE_PATH_DATA="${datadir}"
OE_QMAKE_PATH_BINS="${bindir}"
OE_QMAKE_PATH_LIBEXECS="${libdir}/${QT_DIR_NAME}/libexec"
OE_QMAKE_PATH_PLUGINS="${libdir}/${QT_DIR_NAME}/plugins"
OE_QMAKE_PATH_IMPORTS="${libdir}/${QT_DIR_NAME}/imports"
OE_QMAKE_PATH_QML="${libdir}/${QT_DIR_NAME}/qml"
OE_QMAKE_PATH_TRANSLATIONS="${datadir}/translations"
OE_QMAKE_PATH_SETTINGS="${sysconfdir}"
OE_QMAKE_PATH_EXAMPLES="${datadir}/examples"
OE_QMAKE_PATH_TESTS="${datadir}/tests"
OE_QMAKE_PATH_HOST_PREFIX=""
OE_QMAKE_PATH_HOST_BINS="${bindir}/${QT_DIR_NAME}"
OE_QMAKE_PATH_HOST_DATA="${QMAKE_MKSPEC_PATH_TARGET}"

# for qt5 components we're using QT_DIR_NAME subdirectory in more
# variables, because we don't want conflicts with qt4
# This block is usefull for components which install their
# own files without QT_DIR_NAME but need to reference paths e.g. 
# with QT headers
OE_QMAKE_PATH_QT_HEADERS="${includedir}/${QT_DIR_NAME}"
OE_QMAKE_PATH_QT_ARCHDATA="${libdir}/${QT_DIR_NAME}"
OE_QMAKE_PATH_QT_DATA="${datadir}/${QT_DIR_NAME}"
OE_QMAKE_PATH_QT_BINS="${bindir}/${QT_DIR_NAME}"
OE_QMAKE_PATH_QT_TRANSLATIONS="${datadir}/${QT_DIR_NAME}/translations"
OE_QMAKE_PATH_QT_DOCS="${docdir}/${QT_DIR_NAME}"
OE_QMAKE_PATH_QT_SETTINGS="${sysconfdir}/${QT_DIR_NAME}"
OE_QMAKE_PATH_QT_EXAMPLES="${datadir}/${QT_DIR_NAME}/examples"
OE_QMAKE_PATH_QT_TESTS="${datadir}/${QT_DIR_NAME}/tests"

./configure -v \
 -commercial -confirm-license \
 -sysroot /home/alex.moore/qt5.3 \
 -extprefix /home/alex.moore/qt5.3/pkg \
 -no-gcc-sysroot \
 -no-libjpeg \
 -no-gif \
 -no-accessibility \
 -no-cups \
 -no-nis \
 -no-gui \
 -no-qml-debug \
 -no-sql-mysql \
 -no-sql-sqlite \
 -no-opengl \
 -no-openssl \
 -no-xcb \
 -verbose \
 -release \
 -prefix ${prefix} \
 -bindir ${OE_QMAKE_PATH_BINS} \
 -libdir ${libdir} \
 -datadir ${OE_QMAKE_PATH_DATA} \
 -sysconfdir ${OE_QMAKE_PATH_SETTINGS} \
 -docdir ${docdir} \
 -headerdir ${OE_QMAKE_PATH_HEADERS} \
 -archdatadir ${libdir} \
 -libexecdir ${OE_QMAKE_PATH_LIBEXECS} \
 -plugindir ${OE_QMAKE_PATH_PLUGINS} \
 -importdir ${OE_QMAKE_PATH_IMPORTS} \
 -qmldir ${OE_QMAKE_PATH_QML} \
 -translationdir ${OE_QMAKE_PATH_TRANSLATIONS} \
 -testsdir ${OE_QMAKE_PATH_TESTS} \
 -no-glib \
 -no-iconv \
 -silent \
 -nomake examples \
 -nomake tests \
 -nomake libs \
 -no-compile-examples \
 -no-rpath \
 -static \
 -silent \
 -no-pch \
 -no-rpath \
 -pkg-config

