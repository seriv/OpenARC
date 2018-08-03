# Copyright (c) 2010, 2011, 2016, 2017 The Trusted Domain Project.
# All rights reserved.

Summary:	An open source library and milter for providing ARC service
Name:		openarc
Version:	1.0.0.beta0
Release:	8.3
%define DebianRelease 2
License:	BSD-2-Clause
Group:		System Environment/Daemons
Requires:	libopenarc0 = %{version}-%{release}
BuildRequires:	openssl-devel, xz
BuildRequires:	libbsd-devel
BuildRequires:	sendmail-devel
Source: openarc-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-root
Prefix: %{_prefix}

URL:		https://openarc.org/
# as long as ./configure is not shipped...
BuildRequires:	automake
BuildRequires:	libtool
BuildRequires:	xz

######### SUSE ####################
%if 0%{?suse_version} >= 1200
PreReq: pwdutils
# https://en.opensuse.org/openSUSE:Systemd_packaging_guidelines
BuildRequires: systemd-rpm-macros
%{?systemd_requires}
%endif

######### Fedora #################
%if 0%{?fedora_version} >= 26
Requires: shadow-utils
BuildRequires: sendmail-milter-devel
BuildRequires: libbsd-devel
%endif

%if 0%{?fedora_version} > 27
# Package "system-release" exist as
# - fedora-modular-release
# - generic-release
# fedora-modular-release don't exist on build.opensuse.org
BuildRequires: generic-release
%endif

%description
The Trusted Domain Project is a community effort to develop and maintain a
C library for producing ARC-aware applications and an open source milter for
providing ARC service through milter-enabled MTAs.

%package -n libopenarc0
Summary: An open source ARC library
Group: System/Libraries

%description -n libopenarc0
This package contains the library files required for running services built
using libopenarc.

%package -n libopenarc-devel
Summary: Development files for libopenarc
Group: Development/Libraries/C and C++
Requires: libopenarc0 = %{version}
Requires: libbsd-devel

%description -n libopenarc-devel
This package contains the static libraries, headers, and other support files
required for developing applications against libopenarc.

%prep
%setup -n %{name}-%{version}

%build
aclocal
autoreconf -i || :
./configure --prefix=%{_prefix} --sysconfdir=%{_sysconfdir} --libdir=%{_libdir} --mandir=%{_mandir}
make

%install
make install DESTDIR="$RPM_BUILD_ROOT"
%if 0%{?rhel} >= 7
install -D -m 0644 contrib/systemd/%{name}.service %{buildroot}%{_unitdir}/%{name}.service
%elif 0%{?rhel} >= 6
mkdir -p "$RPM_BUILD_ROOT"%{_initrddir}
install -m 0755 contrib/init/redhat/openarc "$RPM_BUILD_ROOT"%{_initrddir}/%{name}
%else
mkdir -p "$RPM_BUILD_ROOT"%{_initrddir}
install -m 0755 contrib/init/generic/openarc "$RPM_BUILD_ROOT"%{_initrddir}/%{name}
%endif
ln -s service %{buildroot}%{_sbindir}/rc%{name}

%if 0%{?rhel} >= 7
# BUG? remove macros from service file
sed -i -e 's|${prefix}||' -e 's|${exec_prefix}|/usr|' %{buildroot}%{_unitdir}/%{name}.service
%endif

# BUG? installed "doc files" have no content anyway...
rm -r "$RPM_BUILD_ROOT"%{_prefix}/share/doc/openarc

install -p -d "$RPM_BUILD_ROOT"%{_sysconfdir}/
cat > "$RPM_BUILD_ROOT"%{_sysconfdir}/openarc.conf <<EOF
# Basic OpenARC config file
PidFile /run/openarc/openarc.pid
Syslog	yes
UserID openarc:mail
#
Socket local:/run/openarc/openarc.socket
#
Domain example.com
Selector seal
KeyFile %{_sysconfdir}/openarc/seal.private
EOF

install -p -d "$RPM_BUILD_ROOT"/usr/lib/tmpfiles.d/
cat > "$RPM_BUILD_ROOT"/usr/lib/tmpfiles.d/%{name}.conf <<EOF
D /run/%{name} 0755 %{name} %{name} -
EOF

%pre
getent group  openarc >/dev/null || %{_sbindir}/groupadd -r openarc
getent passwd openarc >/dev/null || %{_sbindir}/useradd  -r -g openarc -d %{_localstatedir}/lib -s /bin/false -c "OpenARC daemon" openarc
getent group  mail    >/dev/null && %{_sbindir}/usermod  -G mail openarc
%if 0%{?suse_version} >= 1200
%service_add_pre openarc.service
%else
%endif

%post
if [ ! -d %{_sysconfdir}/openarc ]; then
	mkdir %{_sysconfdir}/openarc
	chmod o-rx %{_sysconfdir}/openarc
  openssl genrsa -out %{_sysconfdir}/openarc/seal.private
  chmod 0640 %{_sysconfdir}/openarc/seal.private
	chown -R openarc:openarc %{_sysconfdir}/openarc
fi
if [ -x /sbin/chkconfig ]; then
        /sbin/chkconfig --add openarc
elif [ -x /usr/lib/lsb/install_initd ]; then
        /usr/lib/lsb/install_initd openarc
fi
%tmpfiles_create %_tmpfilesdir/%{name}.conf
%service_add_post openarc.service
# enable the service
ln -s %{_unitdir}/%{name}.service %{_sysconfdir}/systemd/system/multi-user.target.wants/%{name}.service || :
# start the service
%{_sbindir}/rc%{name} start || :

%preun
%if 0%{?suse_version} >= 1200
%service_del_preun openarc.service
%else
if [ $1 = 0 ]; then
	service openarc stop && rm -f %{_localstatedir}/run/openarc/openarc.sock && rmdir %{_localstatedir}/run/openarc 2>/dev/null
	if [ -x /sbin/chkconfig ]; then
		/sbin/chkconfig --del openarc
	elif [ -x /usr/lib/lsb/remove_initd ]; then
		/usr/lib/lsb/remove_initd openarc
	fi
	userdel openarc
	if getent group openarc >/dev/null; then
		groupdel openarc
	fi
fi
%endif


%postun
%if 0%{?suse_version} >= 1200
%service_del_postun openarc.service
#%else
%endif

%post -n libopenarc0 -p /sbin/ldconfig

%postun -n libopenarc0 -p /sbin/ldconfig

%clean
if [ "$RPM_BUILD_ROOT" != "/" ]; then
	rm -rf "$RPM_BUILD_ROOT"
fi

%files
%defattr(-,root,root)
%doc LICENSE LICENSE.Sendmail README RELEASE_NOTES
%doc openarc/openarc.conf.sample openarc/openarc.conf.simple
%config(noreplace) %{_sysconfdir}/openarc.conf
%config %{_initrddir}/%{name}
%{_mandir}/*/*
%{_sbindir}/*
%if 0%{?suse_version} >= 1200
%{_unitdir}/%{name}.service
/usr/lib/tmpfiles.d/%{name}.conf
%else
%if 0%{?redhat} >= 7
/usr/lib/systemd/system/%{name}.service
%else
%config %{_initrddir}/%{name}
%endif

/usr/lib/tmpfiles.d/%{name}.conf
%endif
%ghost %attr(755, openarc, openarc) /run/%{name}

%files -n libopenarc0
%defattr(-,root,root)
%{_libdir}/*.so.*

%files -n libopenarc-devel
%defattr(-,root,root)
%{_includedir}/*
%{_libdir}/*.a
%{_libdir}/*.la
%{_libdir}/*.so
%{_libdir}/pkgconfig/*.pc

%changelog
* Fri Aug 03 2018 <seriv@cs.umd.edu> - 1.0.0.beta0-8.3
- Made installable for RHEL6
* Wed Aug 01 2018 <rpmbuild@openarc.org> - 1.0.0
- Fix https://github.com/trusteddomainproject/OpenARC/issues/100
- Fix https://github.com/trusteddomainproject/OpenARC/issues/102
* Thu Jul 26 2018 <rpmbuild@openarc.org> - 1.0.0
- Version 1.0.0.Beta0
* Thu Feb 22 2018 <rpmbuild@openarc.org> - 0.1.0
- SLES11 removed
- CentOS-7 added
* Fri Dec 08 2017 <rpmbuild@openarc.org> - 0.1.0
- build for SLES11
* Thu Dec 07 2017 <rpmbuild@openarc.org> - 0.1.0
- git checkout develop -> commit 495aff7 fix for
  https://github.com/trusteddomainproject/OpenARC/issues/47
* Wed Dec 06 2017 <rpmbuild@openarc.org> - 0.1.0
- git clone (latest commit  0b955c3 from 20171206
* Mon Nov 27 2017 <rpmbuild@openarc.org> - 20171127
- git clone (latest commit 8ee5d92 from 20171123)
* Thu Nov 09 2017 <rpmbuild@openarc.org> - 20171109
- postinst: don't require packager's staff
* Fri Oct 13 2017 <rpmbuild@openarc.org> - 20171013
- git clone (latest commit 1bb9999 from 20171012)
* Fri Sep 15 2017 <rpmbuild@openarc.org> - 20170915
- git clone (latest commit 942cd16 from 20170913)
* Tue Sep 12 2017 <rpmbuild@openarc.org> - 20170912
- git clone
* Thu Aug 03 2017 <rpmbuild@openarc.org> - 20170803
- git clone, https://github.com/mskucherawy/OpenARC/commit/b3faba121c07bce32d04895ee1c9f4278669a835
* Sun Jul 30 2017 <rpmbuild@openarc.org> - 20170730
- specfile for openSuSE:Leap:42.3
