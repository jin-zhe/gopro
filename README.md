# GoPro: Telemetry extractor in Python
This project is a simple Python wrapper for the [GoPro utilities](https://github.com/stilldavid/gopro-utils) provided by [@stilldavid](https://github.com/stilldavid)

Specifications:
* Python 3.5
* Ubuntu 16.04
* Videos captured on GoPro Hero 5 black

## Prerequisites
* [FFmpeg](https://ffmpeg.org/)
* [GoLang](https://golang.org/)

## Instructions

### Compile GoPro telemetry extraction executables
The following guide is adapted from [here](https://community.gopro.com/t5/Cameras/Hero5-Session-Telemetry/m-p/40278/highlight/true#M20188)

Clone the necessary repositories with the correct directory structure
```sh
mkdir -p $HOME/go/src/github.com/stilldavid/
git clone git@github.com:stilldavid/gopro-utils.git $HOME/go/src/github.com/stilldavid/gopro-utils
mkdir -p $HOME/go/src/github.com/paulmach
git clone git@github.com:paulmach/go.geo.git $HOME/go/src/github.com/paulmach
git clone git@github.com:paulmach/go.geojson.git $HOME/go/src/github.com/paulmach
```

To extract Gyro, Accel and Temp information in spreadsheet format, we need to do the following
```sh
cd $HOME/go/src/github.com/stilldavid/gopro-utils/bin/gpmdinfo/
mv gpmdinfo.go gpmdinfo.go.bkup
wget http://tailorandwayne.com/gpmdinfo.go
```

If you're using a GoPro Hero 5 Black, open the `gpmdinfo.go` and uncomment the all blocks marked with "Uncomment for Gps":
```go
///////////////////////Uncomment for Gps
var gpsCsv = [][]string{{"Latitude","Longitude","Altitude","Speed","Speed3D","TS"}}
gpsFile, err := os.Create("gps.csv")
checkError("Cannot create gps.csv file", err)
defer gpsFile.Close()
gpsWriter := csv.NewWriter(gpsFile)

// ...

////////////////////Uncomment for Gps
for i, _ := range t.Gps {
  gpsCsv = append(gpsCsv, []string{floattostr(t.Gps[i].Latitude),floattostr(t.Gps[i].Longitude),floattostr(t.Gps[i].Altitude),floattostr(t.Gps[i].Speed),floattostr(t.Gps[i].Speed3D),int64tostr(t.Gps[i].TS)})
}

// ...

/////////////Uncomment for Gps
for _, value := range gpsCsv {
    err := gpsWriter.Write(value)
    checkError("Cannot write to gps.csv file", err)
}
defer gpsWriter.Flush()    
```

Finally build the executables
```sh
cd $HOME/go/src/github.com/stilldavid/gopro-utils/bin/gpmdinfo/
go build
#=> Creates 'gpmdinfo' within the directory
cd $HOME/go/src/github.com/stilldavid/gopro-utils/bin/gopro2gpx/
go build
#=> Creates 'gopro2gpx' within the directory
cd $HOME/go/src/github.com/stilldavid/gopro-utils/bin/gopro2json/
go build
#=> Creates 'gopro2json' within the directory
```

### Configure
We need to tell our python script where to look for the executables we compiled

```sh
cd <THIS REPOSITORY>
cp config.yml.example config.yml
```
If you have followed the instructions exactly up to this point, then there's no need to edit the config file. Else, just make sure the paths point to the correct respective executables you just compiled
