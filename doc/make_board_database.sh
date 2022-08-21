mkdir -p dts_temp
west boards > device_list.txt

while IFS= read -r line; do
  echo west build -d dts_temp/build -p -b $line ../samples/hello_world
  west build -d dts_temp/build -p -b $line ../samples/hello_world
  cp dts_temp/build/zephyr/zephyr.dts dts_temp/$line.dts
done < device_list.txt

rm dts_temp/qemu_*
rm dts_temp/xt-sim*
python make_board_database.py
